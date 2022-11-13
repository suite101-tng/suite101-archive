// Landing Page View
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'views/PagedListView'
],
function(
    $,
    Backbone,
    _,
    suiteio,
    PagedListView
) {
    'use strict';
    var LandingView = Backbone.View.extend({
        events: function() {
            return _.extend({
                'click .createAccount': 'createAccount',
                'click .scrollToContent': 'scrollToContent'
            },
            _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function (options) {
            var self = this;
            this.templatePromise = suiteio.templateLoader.getTemplate('home', ['story-teaser']);
            this.rootUrl = '/';
            this.skipRender = options.skipRender || false;
            
            this.windowHeight = suiteio.getWindowSize().height;
            var $el = $('#landing-view');
            // $el.find('.tip').tooltip('destroy').tooltip();
            if($el.length) {
                this.setElement($el);
                this.startStoryPager();
                this.trigger('renderComplete', this.$el);
            } else {
                console.log('hey, we do not have length...');
                // this.render();
            }
        },

        fetchContext: function() {
            var self = this;
            return $.ajax({
                url: self.rootUrl,
                type: 'GET',
                data: {
                    spa: true
                }
            });
        },

        render: function() {
            var self = this;
            var $el;
            var $html;
            this.fetchContext().then(function(context) {
                self.templatePromise.done(function(tmpl) {
                    $html = $(tmpl(context));
                    if($html.length > 1) {
                        $el = $('<div/>').append($html);
                    } else {
                        $el = $html.eq(0);
                    }
                    if(self.$el.is(':empty')) {
                        //first time render
                        self.setElement($el);
                    } else {
                        self.$el.html($html.html());
                    }
                    self.trigger('renderComplete', self.$el);
        
                }); 
            });     
        },

        afterRender: function() {
            console.log('after render...');
            this.startStoryPager();
        },

        startStoryPager: function() {
            var self = this;
            var url = this.rootUrl;
            var $listViewEl = this.$('.landingFeaturedStories');

            // self.featStoriesListView && self.mySuitesListView.destroy();
            this.featStoriesListView = new PagedListView({
                    el: $listViewEl,
                    url: url,
                    templateName: 'story-teaser',
                    name: 'featuredstorieslist'
            });
            self.listenToOnce(self.featStoriesListView, 'listViewReady', function() {
                self.featStoriesListView.fetch();
            });
            self.listenToOnce(self.featStoriesListView, 'errorFetchingCollection' || 'noListViewResults', function() {
                console.log('No results');
                self.$('.mySuites .paginatedList').html('');
            });
        },

        scrollToFirst: function() {
            var offset = this.windowHeight / 1.5;
            $('body').velocity("scroll", { 
              duration: 500,
              easing: [ 0.19, 1, 0.22, 1 ],
              offset: offset
            });
        },

        followSuite: function(e) {
            suiteio.followSuite(e);
        },

        followUser: function(e) {
            suiteio.followUser(e);
        },

        fromParentMiniCreate: function(e) {
            suiteio.respondTo(e, true);
        },

        respondTo: function(e) {
            suiteio.respondTo(e);
        },
        
        openSuiteSelector: function(e) {
            suiteio.openSuiteSelector(e);
        },

        createAccount: function(e) {
            if(!suiteio.loggedInUser) {
                suiteio.fireLoginModal(false); // join = true
            return;
            }
        },

        loginModal: function(e) {
            if(!suiteio.loggedInUser) {
                suiteio.fireLoginModal();
            return;
            }
        },
       
        destroy: function() {
            this.featStoriesListView && this.featStoriesListView.destroy();
            Backbone.View.prototype.destroy.apply(this, arguments);
        }
    });
    return LandingView;
});
