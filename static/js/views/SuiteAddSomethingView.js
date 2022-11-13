// SuiteAddSomethingView.js
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'views/PagedListView'
], function(
    $,
    Backbone,
    _,
    suiteio,
    PagedListView
    ) {
    'use strict';
    var SuiteAddSomethingView = Backbone.View.extend({
        events: function() {
            return _.extend({

                'click .postSelectorItem': 'somethingSelect',
                // 'keyup .ctxtSearchInput': _.debounce(this.somethingKeyup, 400)                
                // 'hide.bs.modal': 'exit'
            }, _.result(Backbone.View.prototype, 'events'));
        },
        initialize: function (options) {
            this.addModalTmplPromise = suiteio.templateLoader.getTemplate('suite-add-something-modal'); 
            this.options = options || '';
            this.suiteId = options.suiteId || '';
            this.rootUrl = '/s/api/add_something/' + this.suiteId;
        },

        openAddModal: function() {  
            var self = this;
            var $storyId = self.contentId || '';

            this.addModalTmplPromise.done(function(tmpl) {
                self.addModal = $(tmpl({
                    storyTitle: self.contentTitle
                }));
                self.addModal.modal(); 
                self.setElement(self.addModal);
                self.setupSomethingPagedList();    

            });

        },

        closeModal: function() {
            this.addModal.modal('hide');
        },

        setupSomethingPagedList: function() {
            var self = this;
            var $listViewEl = this.$('.somethingList');
            var startPage = 1;
            var searchArr = window.location.search.split('=');
            var namedFilter = this.namedFilter || '';
            var loadFirstPage = true;
            if(searchArr.length >= 2 && searchArr[0] === '?page') {
                startPage = +searchArr[1];
            }
            var url = this.rootUrl;

            this.somethingListView && this.somethingListView.destroy();
            this.somethingListView = new PagedListView({
                firstPage: loadFirstPage,
                namedFilter: namedFilter,
                el: $listViewEl,
                url: url,
                templateName: 'post-selector-teaser',
                name: 'addsomethinglist-' + self.suiteId
            });
            this.listenTo(self.somethingListView, 'listViewFiltered', function(namedFilter) {
                namedFilter = namedFilter || '';
                // if(namedFilter=='suite') {
                //     this.somethingListView.templateName = 'suite-story-teaser';
                // } else if(namedFilter=='user') {
                //     this.somethingListView.templateName = 'user-teaser';
                // }
                self.somethingListView.fetch();
            });            
            this.listenToOnce(self.somethingListView, 'listViewReady', function() {
                self.somethingListView.fetch();
            });            
        },

        // somethingKeyup: function(e) {
        //     e.preventDefault();
        //     console.log('hey');
        // },

        somethingSelect: function(e) {
            var self = this;
            var $target = $(e.currentTarget);
            var $button = $target.find('.somethingToggle');
            var contentId = $target.data('id');
            var contentType = $target.data('type');

            $button.dynamicButton({immediateEnable: true});
            $.ajax({
                url: self.rootUrl,
                type: 'POST',
                data: {
                    contentid: contentId,
                    contenttype: contentType
                },
                success: function(isActive) {
                    $button && $button.dynamicButton('revert');
                    if(isActive) {
                        $target.addClass('active');
                    } else {
                        $target.removeClass('active');
                    }
                    console.log('triggering suitePostsUpdated!');
                    self.trigger('suitePostsUpdated');
                }
            });                
          
        },        

        createNewSuite: function() {
            suiteio.createSuiteModal(true);
        },

        exit: function(e) {
            this.trigger('closeSuiteAddSomethingView');
            this.$el.modal('hide');
            this.$el.remove();
        },

        destroy: function() {
            Backbone.View.prototype.destroy.apply(this, arguments);
            this.$el.remove();
        },

    });
    return SuiteAddSomethingView;
});