// ExploreDetail
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'views/FeedView',
    'views/LandingView',
    'views/SearchView',
    'views/ExploreView'
], function(
    $,
    Backbone,
    _,
    suiteio,
    FeedView,
    LandingView,
    SearchView,
    ExploreView
) {
    'use strict';
    var ExploreDetail = Backbone.View.extend({
        initialize: function(options) {
            options = options || {};
            this.id = 'ExploreController';
            if(options.el) {
                this.setElement(options.el);
            }
            suiteio.pageController.registerController(this);
            this.listenTo(suiteio.pageController, 'closeDown-ExploreController', function() {
                this.clearViews();
            });
            this.viewType = '';            
            this.searchOpen = false;
         },

         loadFeedView: function(options) {
            var self = this;
            options = options || {};
            var skipRender = options.skipRender || false;
            var rebuildMe = options.rebuildMe || false; // rebuild feed if empty...
            var metaAttrs = {
                title: 'Suite',
                meta: [{
                    'name': 'description',
                    'content': 'Suite is a simpler, more conversational way to share our stories.'
                }]
            };            
            this.clearViews();
            if(suiteio.loggedInUser) {
                this.feedView = new FeedView({
                    skipRender: skipRender,
                    rebuildMe: rebuildMe
                });
            } else {
                this.feedView = new LandingView({
                    skipRender: skipRender
                });
            }
            this.listenToOnce(self.feedView, 'renderComplete', function($el) {
                // this.setupStorySupplementaryViews();
                this.updateMeta(metaAttrs);

                self.listenToOnce(suiteio.pageController, 'renderdone-'+self.id, function() {
                    self.feedView.afterRender();
                });

                self.trigger('pageChange', self, self.feedView.$el, '', {
                    trigger: false
                });
            });
            if(!skipRender) {
                this.feedView.render();
            } 
        },


         loadExploreView: function(options) {
            var self = this;
            this.viewType = options.viewType || '';
            this.currentTab = options.currentTab || '';
            var skipRender = options.skipRender || false;
            var exploreUrl = '/' + this.viewType;
            var metaTitle, metaDescription;

            switch(this.viewType) {
                case 'latest':
                    metaTitle = 'Latest posts';
                    metaDescription = 'Recent stories from all around Suite'
                break;
                case 'long':
                    metaTitle = 'Long reads';
                    metaDescription = 'A selection of longer posts.'                
                break;
                case 'top':
                    metaTitle = 'Top post';
                    metaDescription = 'Most read posts from everyone'                
                break;
                case 'people':
                    metaTitle = 'Featured members';
                    metaDescription = 'A selection of our most active, read, inspiring members.'                
                break;
                case 'discussed':
                    metaTitle = 'Discussed';
                    metaDescription = 'Actively discussed stories from all around Suite'                
                break;
                case 'explore':
                    metaTitle = 'Explore';
                    metaDescription = 'Browse all the recent, most read, most discussed stories on Suite.'                
                break;                
            }
            var metaAttrs = {
                title: metaTitle,
                meta: [{
                    'name': 'description',
                    'content': metaDescription
                }]
            };            
            this.clearViews();
            this.exploreView = new ExploreView(options);

            this.listenTo(this.exploreView, 'changeExploreTab', function(newTab) {
                self.currentTab = newTab;
                self.loadExploreView({
                    viewType: self.currentTab
                });
            });

            this.listenToOnce(this.exploreView, 'renderComplete', function($el, viewType) {
                // this.setupStorySupplementaryViews();
                this.updateMeta(metaAttrs);

                self.listenToOnce(suiteio.pageController, 'renderdone-'+self.id, function() {
                    // after render
                });

                self.trigger('pageChange', self, self.exploreView.$el, exploreUrl, {
                    trigger: false
                });
            });
            if(!skipRender) {
                this.exploreView.render();
            }

        },

        toggleNavSearch: function(e) {
            if(this.searchOpen) {
                console.log('close search please');
                this.searchView.closeNavSearch();
            } else {
                console.log('open search please');
                this.openSearch();
            }
        },

        openSearch: function() {
            var self = this;
            this.searchOpen = true;
            this.clearViews('searchView');
            this.searchView = new SearchView();
            this.searchView.render();
            this.listenToOnce(this.searchView, 'searchClosed', function() {
                self.stopSearch();
            });
        },

        stopSearch: function() {
            this.searchOpen = false;
            this.clearViews('searchView');
        },

        updateMeta: function(attrs) {
            suiteio.metaHandler.updateHead(attrs);
        },

        clearViews: function(views) {
            views = views || ['feedView', 'searchView', 'exploreView'];
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
            Backbone.View.prototype.destroy.apply(this, arguments);
        }

    });
    return ExploreDetail;
});