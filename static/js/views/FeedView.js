//FeedView
define([
    'jquery',
    'backbone',
    'suiteio',
    'views/PagedListView',
    'views/TourView'
],
function(
    $,
    Backbone,
    suiteio,
    PagedListView,
    TourView
) {
    'use strict';
    var FeedView = Backbone.View.extend({
        events: function() {
            return _.extend({
                'show.bs.tab .feedTab[data-toggle="tab"]': 'tabChange',
                'click .storyTeaserBody': 'toggleFullTeaser'
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function (options) {
            var self = this;
            // this.$el = $('.notifsContainer');
            // this.setElement($('.notifsContainer'));
            this.templatePromise = suiteio.templateLoader.getTemplate('feed', ['story-teaser']);
            this.feedType = 'all'
            options = options || {};
            this.rebuildMe = options.rebuildMe || false;
            console.log('init rebuildMe? ' + self.rebuildMe);

            var $el = $('#feed-view');
            if($el.length) {
                this.setElement($el);
                this.afterRender();
            } else {
                // this.render();
            }
        },

        fetchContext: function(fetchType) {
            var self = this;
            fetchType = fetchType || '';
            this.fetchComplete = false;
            var context = $.ajax({
                url: '/',
                type: 'GET',
                data: {
                    feedtype: self.feedType,
                    spa: true,
                    fetchType: fetchType
                }
            });
            return context;
        },

        modAction: function(e) {
            suiteio.pageController.modThis(e);
        },
        
        render: function() {
            var self = this;
            var $el;
            var $html;
            this.fetchContext().then(function(context) {
                self.fetchComplete = true;
                self.rebuildMe = context.rebuildMe || false;
                console.log('render() rebuildMe? ' + self.rebuildMe);
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
            console.log('after render!');
            this.startUpFeed();
        },

        showTour: function() {
            if(suiteio.loggedInUser && suiteio.loggedInUser.get('showTour')) {
                this.tour = new TourView();
                this.tour.loadTour();
            }
        },

        rebuildFeed: function() {
            var self = this;
            var progressNote = '<div class="feed-rebuild rebuildingFeed centered"><div class="loading-block"><i class="io io-suite io-spin-rev"></i></div><div class="texty">Setting up your story feed...</div></div>';
            var $feedEl = this.$('.storyFeed .paginatedList');
            $feedEl.html(progressNote);
            this.$('.rebuildingFeed').velocity('stop', true).velocity("fadeIn", 200);            
            this.fetchContext('rebuild').then(function(added) {
                self.rebuildMe = 0; // don't do it again
                self.loadFirstPage = true;
                self.startUpFeed();
            });
        },

        startUpFeed: function() {
            var self = this;
            var feedType = this.feedType;
            var $listViewEl;
            var url;
            var loadFirstPage = this.loadFirstPage || false;

            console.log(this.rebuildMe);
            if(this.rebuildMe) {
                this.rebuildFeed();
                return;
            } else {
                this.$el.find('.tip').tooltip('destroy').tooltip();
                if(self.storyFeedListView) {
                    self.storyFeedListView && self.storyFeedListView.destroy();
                }
                switch(feedType) {
                    case 'long':
                        $listViewEl = $('.feedLong')
                        url = '/?feed=long';
                    break;
                    default:
                        $listViewEl = self.$('.storyFeed')
                        url = '/?feed=all';
                    break;                
                }

                self.storyFeedListView = new PagedListView({
                        el: $listViewEl,
                        firstPage: loadFirstPage,
                        url: url,
                        templateName: 'story-teaser',
                        name: 'myfeed-' + feedType
                });
                self.listenToOnce(self.storyFeedListView, 'listViewReady', function() {
                    self.storyFeedListView.fetch();
                });                
            }
        },

        tabChange: function(e) {
            console.log('tab change?');
            var tab = $(e.currentTarget).data('target');
            this.feedType = tab.replace('#', '').split('-')[0];
            console.log('feedtype? ' + this.feedType);
            this.render();
        },

        toggleFullTeaser: function(e) {
            suiteio.toggleFullTeaser(e);
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
        
        openSuiteSelector: function(e) {
            suiteio.openSuiteSelector(e);
        },
      
        storyTeaserBodyGo: function(e) {
            var $currentTarget = $(e.currentTarget);
            var $href = $currentTarget.find('.titleLink').attr('href');
            suiteio.pageController.navigate($href, {trigger: true});
        },

        closeAlert: function(e) {
            var $target = $(e.currentTarget),
                url = $target.attr('href'),
                alert = $target.data('alert');

            $.ajax({
                url: url,
                type: 'POST',
                data: {
                    a_id: alert = alert
                },
                success: function() {
                    $('.alertBox').remove();
                }
            });
        },
        destroy: function() {
            Backbone.View.prototype.destroy.apply(this, arguments);
        }
    });
    return FeedView;
});