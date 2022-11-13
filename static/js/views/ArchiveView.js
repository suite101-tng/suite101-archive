// ArchiveView
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'lib/underwood',
    'views/PagedListView',
    'taggle'
], function(
    $,
    Backbone,
    _,
    suiteio,
    Underwood,
    PagedListView,
    Taggle
) {
    'use strict';
    var ArchiveView = Backbone.View.extend({
        events: function() {
            return _.extend({
                // 'click .toggleNotifSend': 'toggleAccrualNotify'
                'click .acceptRejectInvite': 'suiteInviteAcceptReject',
                'show.bs.tab .notifTab[data-toggle="tab"]': 'tabChange'
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function (options) {
            var self = this;
            this.utilityUrl = '/admin/api/archive';
            this.urlRoot = '/archived'
            this.$listViewEl = options.el || '';
            this.setupArchiveListView();
            console.log('init archive view');
        },

        setupArchiveListView: function() {
            console.log('setting up archive list view');
            var self = this;
            var url = this.urlRoot;
            console.log('url: ' + url);
            var $listViewEl = $('.archiveList');
            this.archiveListView && this.archiveListView.destroy();
            this.archiveListView = new PagedListView({
                el: $listViewEl,
                firstPage: true,
                url: url,
                templateName: 'story-teaser',
                name: 'archive-list'
            });

            self.listenToOnce(self.archiveListView, 'listViewReady', function() {
                self.archiveListView.fetch();
            });
            self.listenTo(self.archiveListView, 'listViewFiltered', function(namedFilter) {
                namedFilter = namedFilter || '';
                self.archiveListView.fetch();
            });             
            self.listenTo(self.archiveListView, 'noListViewResults', function() {
                console.log('nothing!!!!!!');
                var userName = '';
                self.$('.archiveList .paginatedList').html('<div class="centered no-notifs noNotifs">You have no archive articles to speak of....');
            });
        },

        clearSupplementalViews: function() {
            var views = ['supportQuestionsListView'];
            for(var view, i = 0, l = views.length ; i < l ; i += 1) {
                view = views[i];
                if(this[view]) {
                    this[view].destroy();
                    this.stopListening(this[view]);
                    this[view] = null;
                }
            }
        },

        destroy: function() {
            this.questionTagsInput && this.questionTagsInput.destroy();
            this.clearSupplementalViews();
            Backbone.View.prototype.destroy.apply(this, arguments);
        }

    });
    return ArchiveView;
});