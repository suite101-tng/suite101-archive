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
    var UserView = Backbone.View.extend({
        events: function() {
            return _.extend({
                'click .profileImageContainer': 'tabChange',
                'click .featureMember': 'featureMember',
                'show.bs.tab .profileTab[data-toggle="tab"]': 'tabChange',
                'click .authCard .followButton': 'followUser'
                // 'click .storyTeaserBody': 'goToStoryAction',
            }, _.result(Backbone.View.prototype, 'events'));
        },
        
        initialize: function(options) {       
            var self = this;
            this.model = options.model;
            this.feeds = {};
            this.feedType = options.feedType || '';
            this.followingType = options.followingType || 'user';
            // this.page = options.page || 1;
            if(!this.feedType) {
                this.model.set({
                 homeView: true
              });
            }
            this.templatePromise = suiteio.templateLoader.getTemplate('user-detail', ['suite-teaser', 'post-teaser', 'user-teaser', 'profile-featured-suites']);
            this.profileFeaturedSuitesTmplPromise = suiteio.templateLoader.getTemplate('profile-featured-suites');
            
            this.allRevealed = false;
            this.viewname = 'userdetailview';
            this.bootstrapped = options.bootstrapped || false;

            var $el = $('.pageContainer#user-detail-'+this.model.id);
            if(!this.bootstrapped) {//SPA, expect model to sync
                this.listenToOnce(this.model, 'sync', function() {
                    this.render();
                });
            } 
            if($el.length) {
                this.setElement($el);
                this.trigger('renderComplete', this.$el);
            } 
        },

        fetchExtraContext: function() {
            var self = this;
            var url = this.getRootUrl(this.feedType);
            return $.ajax({
                url: url,
                type: 'GET',
                data: {
                    feed_type: self.feedType,
                    spa: true
                }
            });
        },

        render: function() {
            var self = this;
            var $el;
            var $html;
            var context;
            this.fetchExtraContext().then(function(extraContext) {
                context = $.extend(extraContext, self.model.toJSON());
                self.model.setUserAttributes(extraContext);
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

        getRootUrl: function(feedType) {
            var url = this.model.get('absoluteUrl');
            if(feedType && feedType != "home") {
                url = url + '/' + feedType;
            }
            return url;
        },

        tabChange: function(e) {
            var tab = $(e.currentTarget).data('target');
            var self = this;
            this.feedType = tab.replace('#', '').split('-')[0];
            this.setupFeed(true);
            var url = this.getRootUrl(this.feedType);
            if(this.feedType == 'home') {
                self.$('.profileTab').removeClass('active');
                this.refreshHomeSuites();
            }
            this.trigger('tabChange', url);
        },

        refreshHomeSuites: function() {
            var self = this;
            var $container = this.$('.homeFeatured');
            var featuredSuites = this.model.get('featuredSuites') || '';
            var otherSuites = this.model.get('otherSuites') || '';
            var showMoreSuites = this.model.get('showMoreSuites') || '';
            var stats = this.model.get('stats') || '';
            this.profileFeaturedSuitesTmplPromise.done(function(tmpl) {
                var $html = $(tmpl({
                    featuredSuites: featuredSuites,
                    otherSuites: otherSuites,
                    showMoreSuites: showMoreSuites,
                    stats: stats
                }));
                $container.html($html);
            });
        },

        showAllSuites: function() {
            this.$('.suitesTab').click()
        },

        respondTo: function(e) {
            suiteio.respondTo(e);
        },
        
        openSuiteSelector: function(e) {
            suiteio.openSuiteSelector(e);
        },

        toggleEdit: function() {
            this.trigger('openEditMode', this.model);
        },

        openUserDraftList: function() {
            suiteio.openRightDrawer("storiesPane");
        },

        openUserSettings: function() {
            suiteio.openRightDrawer("settingsPane");  
        },

        // createChat: function(e) {
        //     var userId = $(e.currentTarget).data('id') || '';
        //     suiteio.createNewChat({
        //         chatWith: userId
        //     });
        // },

        afterRender: function(options) {
            var self = this;
            options = options || {};
            // this.setupFeed(null, options.bootstrapped);
            this.setupFeed();
            this.$('.tip').tooltip();
            this.sendProfileView();
        },

        sendProfileView: function() {
            var modelId = this.model.id || '';
            if(!modelId) {
                return;
            }
            var eventData = {
                "event": "profileviews",
                "user": modelId,
                "value": 1,
            }
            suiteio.eventRouter(eventData);
        },

        // goToStoryAction: function(e) {
        //     suiteio.pageController.goToStory(e);
        //     var $currentTarget = $(e.currentTarget);
        //     var $href = $currentTarget.find('.titleLink').attr('href');
        //     suiteio.pageController.navigate($href, {trigger: true});
        // },

        scrollToTop: function(e) {
            var $hero = this.$('.detailCenter');
            $hero.velocity("scroll", { 
              duration: 200,
              offset: -160
            });
        },

        scrollToContentTop: function(e) {
            var $contentPane = this.$('.homeState');
            $contentPane.velocity("scroll", { 
              duration: 200,
              offset: -50
            });
        },

        setupFeed: function(loadFirstPage) {
            var self = this;
            var feedType = this.feedType;
            var templateName, $listViewEl;
            var namedFilter = this.model.get('namedFilter') || '';
            var url = this.getRootUrl(feedType);
            loadFirstPage = loadFirstPage || false;
            var $filterContainer = this.$('.storyListFilter');
            console.log('setting up user feed');
            
            switch(feedType) {
                case 'posts':
                    console.log('-- of type posts');
                    templateName = 'post-teaser';
                    $listViewEl = this.$('section.postsState');
                break;

                case 'suites':
                    templateName = 'suite-teaser';
                    $listViewEl = this.$('section.suiteState');
                break;

                case 'bio':
                break;

                case 'followers':
                    templateName = 'user-teaser';
                    $listViewEl = this.$('section.followersState');
                break;

                case 'following':
                    if(self.followingType=='suite') {
                        templateName = 'suite-teaser';    
                    } else {
                        templateName = 'user-teaser';
                    }
                    $listViewEl = this.$('section.followingState');                
                break;     
                default:
                    templateName = 'story-teaser';
                    $listViewEl = this.$('section.homeState');
                break;
            }
            this.clearViews(['profileListView']);
            this.profileListView = new PagedListView({
                firstPage: loadFirstPage,
                namedFilter: namedFilter,
                el: $listViewEl,
                filterContainer: $filterContainer,
                url: url,
                templateName: templateName,
                name: 'profilelist-' + feedType
            });
            this.listenTo(self.profileListView, 'listViewFiltered', function(namedFilter) {
                namedFilter = namedFilter || '';
                if(namedFilter=='suite') {
                    this.profileListView.templateName = 'suite-teaser';
                } else if(namedFilter=='user') {
                    this.profileListView.templateName = 'user-teaser';
                }
                self.profileListView.fetch();
            });            
            this.listenToOnce(self.profileListView, 'listViewReady', function() {
                self.profileListView.fetch();
            });
        },

        followSuite: function(e) {
            suiteio.followSuite(e);
        },

        followUser: function(e) {
            suiteio.followUser(e);
        },
        
        flagUser: function(e) {
            suiteio.flagIt(e);
        },

        modAction: function(e) {
            suiteio.pageController.modThis(e);
        },

        toggleCaption: function(e) {
            var $container = $('.featureImage');
            $container.toggleClass('open-caption');
            $(document).off('.featureImage').on('click.featureImage keyup.featureImage', function(e) {
                if(e.type === 'keyup') {
                    var code = e.charCode || e.keyCode || e.which;
                    if(code === 27) {
                        $container.removeClass('open-caption');
                    }
                } else if(e.type === 'click') {
                    $container.removeClass('open-caption');
                }
            });


        },

        clearViews: function(views) {
            views = views || ['profileListView'];
            for(var view, i = 0, l = views.length ; i < l ; i += 1) {
                view = views[i];
                if(this[view]) {
                    this.stopListening(this[view]);
                    this[view].destroy();
                    this[view] = null;
                }
            }
        },        

        destroy: function() {
            this.profileListView && this.profileListView.destroy();
            Backbone.View.prototype.destroy.apply(this, arguments);
        }
    });
    return UserView;
});