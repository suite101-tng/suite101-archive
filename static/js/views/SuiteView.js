define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'views/SuiteManageView',
    'views/SuiteAddSomethingView',
    'views/PagedListView'
], function(
    $,
    Backbone,
    _,
    suiteio,
    SuiteManageView,
    SuiteAddSomethingView,
    PagedListView
) {
    'use strict';
    var SuiteView = Backbone.View.extend({
        events: function() {
            return _.extend({        
                    'click .head-fixed': 'scrollToTop',    
                    'show.bs.tab .suiteTab[data-toggle="tab"]': 'tabChange',
                    'click .suitePermalink': 'selectPermalink',
                    'click .storyTeaserBody': 'toggleFullTeaser'
                }, _.result(Backbone.View.prototype, 'events')
            );
        },
        initialize: function(options) {
            var self = this;
            options = options || {};
            this.options = options;
            this.feeds = {};
            this.feedType = 'stories';
            this.isMod = suiteio.loggedInUser && suiteio.loggedInUser.get('isModerator');
            this.templatePromise = suiteio.templateLoader.getTemplate('suite-detail', ['story-teaser', 'suite-teaser', 'suite-hero']);
            this.suiteTeaserTmplPromise = suiteio.templateLoader.getTemplate('suite-teaser');
            this.storyTeaserTmplPromise = suiteio.templateLoader.getTemplate('story-teaser');
            this.suiteRequestModalPromise = suiteio.templateLoader.getTemplate('suite-request-modal');
            this.userTeaserTmplPromise = suiteio.templateLoader.getTemplate('user-teaser');

            this.suiteStoryAdminTeaserTmplPromise = suiteio.templateLoader.getTemplate('suite-story-teaser');  

            this.suiteManageModalTmplPromise = suiteio.templateLoader.getTemplate('suite-manage-modal');
            this.suiteMemberTmplPromise = suiteio.templateLoader.getTemplate('suite-member-item');
           
            this.model = options.model;

            this.listenTo(this.model, 'addStory', this.storyAdded);
            this.listenTo(this.model, 'reset', this.render);
            this.reloadStories = false;
            this.allRevealed = false;
            this.parallaxOn = false;

            if(suiteio.getWindowSize().width < 768) {
                this.smallScreen = true; } else { this.smallScreen = false; }
            if(!options.bootstrapped) {
                this.listenToOnce(this.model, 'sync', function() {
                    this.edViewing = !!(this.model.get('edViewing'));
                    this.render();
                });
            } else {
                var $el = $('.pageContainer#suite-'+this.model.id);
                this.edViewing = !!(this.model.get('edViewing'));
                if($el.length) {
                    this.setElement($el);
                } else {
                    this.needForceRender = true;
                }
            }
        },

        fetchExtraContext: function() {
            // get stories, etc, that we don't want to cache in the api resource
            var self = this;
            var url = this.model.get('absoluteUrl');
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
            var context;
            this.fetchExtraContext().then(function(extraContext) {
                context = $.extend(extraContext, self.model.toJSON());
                self.model.set(extraContext);
                self.templatePromise.done(function(tmpl) {
                    var ctxt = self.model.toJSON(),
                        $html,
                        $el;
                    if(!ctxt.stories && !ctxt.suites) {
                        ctxt.suites = true;
                    }
                    if(suiteio.loggedInUser) {
                        ctxt.userLoggedIn = true;
                        ctxt.edViewing = self.edViewing;
                        if(suiteio.loggedInUser.get('isModerator')) {
                            ctxt.isMod = true;
                        }
                    }
                    $html = $(tmpl(ctxt));
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


        afterRender: function(options) {
            var self = this;
            options = options || {};
            this.setupFeed();

            // Set up manage view
            if(this.model.get('edViewing')) {
                var suite = this.model.toJSON();
                this.manageView = new SuiteManageView( {
                    suite: suite,
                    model: this.model,
                    suiteId: this.model.id
                });   
                
                this.listenToOnce(this.manageView, 'reRenderSuite', function() {
                    this.render();
                });            
            }
            this.sendSuiteView();
            this.$('.tip').tooltip('destroy').tooltip();
            // this.parallax(true);
        },

        openSuiteManageOptions: function() {
            var $manageGroup = this.$('.suiteManageGroup');
            var $openButtons = $manageGroup.find('.whenOpen');
            $manageGroup.addClass('open');               
        },

        closeSuiteManageOptions: function() {
            var $manageGroup = this.$('.suiteManageGroup');
            var $openButtons = $manageGroup.find('.whenOpen');
            $manageGroup.removeClass('open');
        },

        sendSuiteView: function() {
            var modelId = this.model.id || '';
            if(!modelId) {
                return;
            }
            var eventData = {
                "event": "suiteviews",
                "suite": modelId,
                "value": 1,
            }
            suiteio.eventRouter(eventData);
        },

        tabChange: function(e) {
            var tab = $(e.currentTarget).data('target');
            var tabName = tab.replace('#', '').split('-')[0];
            var self = this;
            if(this.feeds[this.feedType]) {
                this.feeds[this.feedType].suspend();
            }
            this.feedType = tabName;
            window.setTimeout(function() {
                self.setupFeed();
            });
        },

        setupFeed: function(loadFirstPage) {
            var feedType = this.feedType;
            var self = this;
            var templateName, $listViewEl;
            var url = this.model.get('absoluteUrl');
            var startPage = 1;
            var searchArr = window.location.search.split('=');
            var namedFilter = this.model.get('namedFilter') || '';
            var loadFirstPage = loadFirstPage || false;
            if(searchArr.length >= 2 && searchArr[0] === '?page') {
                startPage = +searchArr[1];
            }

            switch(feedType) {
                case 'stories':
                    templateName = 'story-teaser';
                    $listViewEl = this.$('.storiesTab');
                break;
                case 'followers':
                    templateName = 'user-teaser';
                    $listViewEl = this.$('.followersTab');
                    loadFirstPage = true;
                break;
            }
            this.suiteListView && this.suiteListView.destroy();
            this.suiteListView = new PagedListView({
                firstPage: loadFirstPage,
                namedFilter: namedFilter,
                el: $listViewEl,
                url: url,
                templateName: templateName,
                name: 'profilelist-' + feedType
            });
            this.listenTo(self.suiteListView, 'listViewFiltered', function(namedFilter) {
                namedFilter = namedFilter || '';
                if(namedFilter=='suite') {
                    this.suiteListView.templateName = 'suite-story-teaser';
                } else if(namedFilter=='user') {
                    this.suiteListView.templateName = 'user-teaser';
                }
                self.suiteListView.fetch();
            });            
            this.listenToOnce(self.suiteListView, 'listViewReady', function() {
                self.suiteListView.fetch();
            });

            suiteio.pageController.navigate(url, {trigger: false});
        },
   
        addSomethingToSuite: function(e) {
            var self = this;
            this.clearSupplementalViews(['addSomethingView']);
            this.addSomethingView = new SuiteAddSomethingView({
                suiteId: self.model.id
            });
            this.addSomethingView.openAddModal();
            this.listenTo(self.addSomethingView, 'suitePostsUpdated', function() {
                console.log('reset feed!');
                // self.render();
                self.setupFeed(true);
            });                        
        },

        modAction: function(e) {
            suiteio.pageController.modThis(e);
        },

        selectPermalink: function(e) {
            e.preventDefault();
            e.stopPropagation();
            var permalink = this.$('.suitePermalink .link');
            permalink.select();
        },

        toggleFullTeaser: function(e) {
            suiteio.toggleFullTeaser(e);
        },

        manageSuite: function() {
            this.manageView.openSuiteManageModal('settings');
        },

        inviteToSuite: function() {
            this.manageView.openSuiteManageModal('users');
        },
       
        respondTo: function(e) {
            suiteio.respondTo(e);
        },
        
        openSuiteSelector: function(e) {
            suiteio.openSuiteSelector(e);
        },

        showSuiteDiscussions: function(e) {
            suiteio.loadChatList(e);
        },

        followSuite: function(e) {
            suiteio.followSuite(e);
        },

        followUser: function(e) {
            suiteio.followUser(e);
        },
        
        editSuiteAction: function(e) {
            this.trigger('openEditMode', this.model);
        },

        flagSuite: function(e) {
            suiteio.flagIt(e);
        },

        scrollToTop: function(e) {
            var $hero = this.$('.detailHero');
            $hero.velocity("scroll", { 
              duration: 200,
              offset: -50
            });
        },

        scrollToContent: function(e) {
            var $contentPane = this.$('.pageOuterWrapper');
            $contentPane.velocity("scroll", { 
                  duration: 200,
                  offset: -50
                });
        },

        toggleCaption: function(e) {
            e.preventDefault();
            var $captionPopup = this.$('.captionPopup'),
                $suiteHeader = this.$('.suiteHeader'),
                self = this;
                
                this.$('.heroImageWrapper').toggleClass('caption-reveal');
                if(this.editing && this.model.get('edViewing')) {
                    this.$('.heroCaptionEdit').toggle();
                } else {
                    this.$('.heroCaption').toggle();
                }

                $(document).off('.hidecaption');
                $(document).on('keydown.hidecaption click.hidecaption', function(e) {
                    if(e.type === 'keydown' && e.which !== 27) { return; }
                    else if (e.type === 'click' && e.target.tagName.toLowerCase().match(/input|textarea/)) { return; }
                    
                    $(this).off('.hidecaption');
                    self.hideCaptionPopup();
                });
        },

        hideCaptionPopup: function() {
            this.$('.heroImageWrapper').removeClass('caption-reveal');
            this.$('.heroCaption').hide();
            this.$('.heroCaptionEdit').hide();
            this.$('.suiteHeader').removeClass('hide-partial');
        },

        clearSupplementalViews: function() {
            var views = ['addSomethingView', 'manageView'];
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
            // this.suiteHeader.destroy();
            this.suiteListView && this.suiteListView.destroy();
            this.clearSupplementalViews();
            // this.parallax(false);
            $(window).off('.hidecaption');
            $(window).off('.hideTitleLink');
            $(document).off('.hidecaption');
            this.$('.pageOuterWrapper').off('.hidecaption');
            Backbone.View.prototype.destroy.apply(this, arguments);
        }
    });
    return SuiteView;
});