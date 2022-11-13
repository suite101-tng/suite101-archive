//PageController
define([
    'jquery',
    'backbone',
    'underscore',
    'StoryDetail',
    'SuiteDetail',
    'UserDetail',
    'NavDetail',
    'ConversationDetail',    
    'ExploreDetail',
    'StaticDetail',
    'LinkDetail',
    'AdminDetail',
    'suiteio'
], function(
    $,
    Backbone,
    _,
    StoryDetail,
    SuiteDetail,
    UserDetail,
    NavDetail,
    ConversationDetail,
    ExploreDetail,
    StaticDetail,
    LinkDetail,
    AdminDetail,
    suiteio
) {
    'use strict';
    var RESOURCETYPE = {
        '1': 'user',
        '2': 'story',
        '3': 'suite',
        '4': 'conversation',
        '5': 'link',
        '6': 'post',
        '13': 'unknown'
    };

    var PageControllerView = Backbone.View.extend({

        el: 'body',

        events: function() {
            return _.extend({
                'click a[data-navigate]': 'linkCatcher'
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function() {
            this.renderStack = [];
            this.$progressBar = $('<div class="progress-bar"></div>');
            $('body').append(this.$progressBar);
            this.$('.pageContainer:visible').addClass('activeView');
        },

        showProgress: function() {
            this.$progressBar.show();
        },
        
        hideProgress: function() {
            this.$progressBar.hide();
        },

        linkCatcher: function(e) {
            var href = {
                prop: $(e.currentTarget).prop('href'),
                attr: $(e.currentTarget).attr('href')
            };

            //http://stackoverflow.com/questions/12081894/backbone-router-navigate-and-anchor-href
            var root = location.protocol + '//' + location.host + Backbone.history.root;

            if (href.prop && href.prop.slice(0, root.length) === root) {
                e.preventDefault();
                Backbone.history.navigate(href.attr, true);
            }
        },



        pushToPageStack: function(cid, $el, doNotTrack) {
            $el
            .css({
                display: 'none'
            })
            this.renderStack.push({
                cid: cid,
                $el: $el,
                doNotTrack: doNotTrack
            });
            this.render();
        },

        render: function() {
            var popped,
                self = this,
                $html = $('html');

            popped = this.renderStack.pop();
            this.$('[data-page-change-remove="true"]').remove();
            $html.removeClass('no-nav').removeClass('hideNav');
            $('body').removeClass('notfound-page cover-page stats');
            if(!this.$('.shell').has(popped.$el).length) {
                this.$('.shell').append(popped.$el);
                popped.resetBodyScroll = true;
            }
            if(this.renderStack.length) {
                this.render();
            } else {
                this.$('.activeView').remove();
                self._showPage(popped);

                // if(this.$('.activeView').length) {
                //    //something to hide?

                //     this.$('.activeView').remove();
                //     // this.$('.activeView').removeClass('activeView')
                //     // .css({
                //     //     display: 'none',
                //     // });
                //     self._showPage(popped);
                // } else {
                //     this._showPage(popped);
                // }
            }
        },

        _showPage: function(popped) {
            var self = this;
            if(popped.resetBodyScroll) {
                $('body').scrollTop(0);
            }
            popped.$el
                .addClass('activeView')
                .css({
                    display: 'block',
                })
                .velocity("transition.fadeIn", 200)
                .promise()
                .done(function() {
                    if(!popped.doNotTrack) {
                        self.activePage = popped;
                    } else {
                        self.activePage = null;
                    }
                    self.trigger('renderdone', popped.cid, popped.$el);
                });
        }

    });
    var PageController = Backbone.Router.extend({
        routes: {
            // Login/reg
            'start': 'passThrough',
            'welcome': 'passThrough',
            'register': 'passThrough',

            // Messages
            'c/:convId': 'loadConversation',

            // Explore
            '': function() {
                this.exploreRoute('feed');
            }, 
            'explore': function() {
                this.exploreRoute('explore');
            },             
            'long': function() {
                this.exploreRoute('long');
            },             
            'latest': function() {
                this.exploreRoute('latest');
            }, 
            'top': function() {
                this.exploreRoute('top');
            }, 
            'suites': function() {
                this.exploreRoute('suites');
            },             
            'discussed': function() {
                this.exploreRoute('discussed');
            }, 
            // Moderation/Admin
            'admin': function() {
                this.adminRoute();
            },
            'admin/stats': function() {
                this.adminRoute('stats');
            },
            'admin/links': function() {
                this.adminRoute('links');
            },                       
            'admin/flags': function() {
                this.adminRoute('flags');
            },             
            'admin/stories': function() {
                this.adminRoute('stories');
            },   
            'admin/suites': function() {
                this.adminRoute('suites');
            },                        
            'admin/tags': function() {
                this.adminRoute('tags');
            },
            'admin/members': function() {
                this.adminRoute('members');
            },
            'admin/royalties': function() {
                this.adminRoute('royalties');
            },         

            // User features
            'notifications': function() {
                this.userRoute('notifications');
            },                       
            'stats': function() {
                this.userRoute('stats');
            },   
            'settings': function() {
                this.userRoute('settings');
            }, 

            'about': function() {
                this.staticRoute('about');
            }, 
            'terms': function() {
                this.staticRoute('terms');
            }, 
            'rules': function() {
                this.staticRoute('rules');
            }, 
            'privacy': function() {
                this.staticRoute('privacy');
            }, 
            'support': function() {
                this.staticRoute('support');
            }, 
            'archived': function() {
                this.staticRoute('archived');
            }, 
            'login': function() {
                this.staticRoute('auth', 'login');
            },             
        
            // Edit/create
            ':slug/edit': 'editProfile',
            'post': 'createStory',

            // Others
            ':slug/rss': 'passThrough',

            ':slug/bio': function(slug) {
                this.slugRoute(slug, 'bio');
            },
            ':slug/stories': function(slug) {
                this.slugRoute(slug, 'stories');
            },
            ':slug/followers': function(slug) {
                this.slugRoute(slug, 'followers');
            },
            ':slug/following': function(slug) {
                this.slugRoute(slug, 'following');
            },            
            ':slug/suites': function(slug) {
                this.slugRoute(slug, 'suites');
            },
            ':type/:hash': 'loadNameHash',
            ':slug': 'slugRoute',
            ':page': 'slugRoute'
        },

        initialize: function(options) {
            this.controllers = {};
            this.pageHistory = {};
            this.view = new PageControllerView();
            this.activeController = null;
            this.pageHistory = {};
            var oldLoadUrl = Backbone.history.loadUrl, self = this;
            Backbone.history.loadUrl = function(fragmentOverride) {
                this.fragment = this.getFragment(fragmentOverride);
                if (self.activeController && self.activeController.isDirty && self.activeController.isDirty()) {
                    var dialog = confirm("Any unsaved changes will be lost when you leave. Click Cancel to stay on the page, click OK to leave page.");
                    if(dialog !== true) {
                        if(self.activeController.id === 'StoryController') {
                            self.navigate('/new', {trigger: false});
                            return true;
                        } 
                    }
                }
                return oldLoadUrl.apply(this, arguments);
            };
            this.listenTo(this.view, 'renderdone', function(cid, $el) {
                this.trigger('pageChangeRenderDone', $el, cid);
                this.trigger('renderdone-'+cid, $el);
            });

        },

        checkHash: function(hash) {
            return $.ajax({
                url: '/decode/' + hash
            });
        },

        route: function(route, name, callback) {
            if (_.isFunction(name)) {
                callback = name;
                name = '';
            }
            if(!callback) { callback = this[name]; }
            var self = this,
                injectedCallback = function() {
                    callback && callback.apply(self, arguments);
                };
            
            Backbone.Router.prototype.route.call(this, route, name, injectedCallback);
        },

        toggleProgress: function(show) {
            if(show) {
                this.view.showProgress();
            } else {
                this.view.hideProgress();
            }
        },


        registerController: function(controller) {
            //controller call this to register itself with PC
            if (controller.id && !this.controllers[controller.id]) {
                this.controllers[controller.id] = controller;
                this.listenTo(controller, 'pageLoading', function() {   
                    this.view.showProgress();
                });
                this.listenTo(controller, 'pageChange', this._pageChangeHandler);
            }
        },

        _pageChangeHandler: function(controller, $el, href, _options) {
            var options = _options || {},
                cid = controller.id;
            //determine if $el is already visible, if not, push it into the render stack
            if((!options.doNotRender) && (!$el.filter(':visible').length || options.replace || !$el.hasClass('activeView'))) {
                this.view.pushToPageStack(controller.id, $el, options.doNotTrack);

                //tell google
                try {
                    ga('send', 'pageview', {page: Backbone.history.location.pathname, title: $('title').text()});
                } catch (e) {

                }
            } else {
                this.trigger('renderdone-'+cid, $el);
            }
            if(options.keepHistory && options.keepHistory.id) {
                if(!this.pageHistory[controller.id]) {
                    this.pageHistory[controller.id] = [];
                }
                this.pageHistory[controller.id].push(options.keepHistory.id);
            }
            if(this.activeController) {
                this.activeController.active = false;
                this.trigger('pageChanging-' + this.activeController.id);
                if (this.activeController.id !== controller.id) {
                    console.log('closing down ' + this.activeController.id);
                    this.trigger('closeDown-' + this.activeController.id);
                }
            }
            suiteio.checkUnread();
            controller.active = true;
            this.activeController = controller;
            if(href) {
                this.navigate(href, {trigger: options.trigger, replace: options.replace});//update url
            }
        },

        registerEventBroadcast: function(events, controller) {
            var passThroughHandler = function(evt) {
                //use this to avoid the function in a loop closure trap
                return function() {
                    var argumentsArr = Array.prototype.slice.call(arguments),
                        args = [evt].concat(argumentsArr);
                    this.trigger.apply(this, args); //Broadcast!
                };
            };
            for(var i=0, l=events.length, evt ; i < l ; ++i) {
                evt = events[i];
                this.listenTo(controller, evt, passThroughHandler(evt));
            }
        },

        getPageHistory: function(key) {
            if (this.pageHistory && this.pageHistory[key]) {
                return this.pageHistory[key];
            }
            return [];
        },

        passThrough: function() {
            //noop
            window.location.reload();
        },

        toggleSearch: function(e) {
            var exploreController = this.controllers['ExploreController'];
            if(!exploreController) {
                exploreController = new ExploreDetail({});
            } 
            exploreController.toggleNavSearch(e);
        },

        editProfile: function(slug) {
            if (!suiteio.loggedInUser) {
                return;
            } else {
                var _slug = suiteio.loggedInUser.get('slug');
                if(_slug===slug || suiteio.loggedInUser.get('isStaff') || suiteio.loggedInUser.get('isModerator')) {
                    if(this.controllers.userDetailController) {
                        this.controllers.userDetailController.editMode();
                    } else {
                        window.location.href = '/' + slug + '/edit';
                    }
                }
            }
        },

        createSuite: function() {
            //create a new suite
            var suiteController = this.controllers['SuiteController'];
            if(!suiteController) {
                suiteController = new SuiteDetail({});
            }
            suiteController.createSuite.apply(suiteController, arguments);
        },

        loadSuite: function(hash, id) {
            var suiteController = this.controllers['SuiteController'];
            if(suiteController) {
                suiteController.loadSuiteFromId(id);
            } else {
                this.controllers['SuiteController'] = suiteController = new SuiteDetail({json: {id: id, hash: hash}});
            }
        },

        loadLink: function(options) {
            var linkController = this.controllers['LinkController'];
            if(!linkController) {    
                this.controllers['LinkController'] = linkController = new LinkDetail({});
            }
            linkController.loadLinkView(options);
        },

        loadNameHash: function(type, hash) {
            var self = this;
            this.checkHash(hash).done(function(response) {
                var type = RESOURCETYPE[response.object_type],
                    id = response.object_id;
                if(type === 'post') {
                    self.loadConversation.apply({convId: id, convHash: hash});
                } else if(type === 'suite') {
                    self.loadSuite.apply(self, [hash, id]);
                } else if(type === 'link') {
                    self.loadLink({ id: id, hash: hash });
                } else if(type === 'conversation') {
                    self.loadConversation({ convId: id, convHash: hash });
                }
            });
        },

        loadStory: function(authorName, id, hash) {
            var storyController = this.controllers['StoryController'];
            if(storyController) {
                storyController.loadStoryFromId(id);
            } else {
                this.controllers['StoryController'] = new StoryDetail({json: {hash: hash, id: id}});
            }
        },

        loadStoryFromModel: function(model) {
            var storyController = this.controllers['StoryController'];
            if(!storyController) {
                storyController = storyController = new StoryDetail({});
            }
            storyController.loadStoryFromModel(model);
        },

        notFound: function() {
            console.log('load not found page!');
            this.staticRoute('notfound');
        },

        exploreRoute: function(viewType) {
            var exploreController = this.controllers['ExploreController'];
            if(!exploreController) {
                exploreController = new ExploreDetail();
            }
            switch(viewType) {
                case 'feed':
                    exploreController.loadFeedView();
                break;              
                default:
                    exploreController.loadExploreView({ viewType: viewType });
                break;                
            }           
        }, 

        staticRoute: function(viewType, subType) {
            var subType = subType || ''
            var staticController = this.controllers['StaticController'];
            if(!staticController) {
                staticController = new StaticDetail();
            }
            staticController.loadStaticView({ viewType: viewType, subType: subType });        
        }, 

        userRoute: function(viewType) {
            var userController = this.controllers['UserController'];
            if(!userController) {
                userController = new UserDetail();
            }
            switch(viewType) {
                case 'notifications':
                    userController.loadNotificationsView({});
                break;
                case 'stats':
                    userController.loadStatsView();
                break;
                case 'settings':
                    userController.loadSettingsView({});
                break;
            }           
        }, 

        createNewConv: function() {
            var convController = this.controllers['ConversationController'];
            if(!convController) {
                convController = new ConversationDetail({});
            } 
            convController.loadChatCreateView.apply(convController, arguments);
        },

        loadNotFound: function() {
            console.log('not found');
        },

        loadConversation: function(options) {
            var convController = this.controllers['ConversationController'];
            if(!convController) {
                convController = new ConversationDetail();
            } 
            convController.loadConvFromId(options);
        },

        unregisterController: function(controller) {
            if (controller.id && this.controllers[controller.id]) {
                this.stopListening(controller);
                this.controllers[controller.id] = null;
            }
        },

        hashChange : function(evt) {
            //http://mikeygee.com/blog/backbone.html
            if(this.cancelNavigate) { // cancel out if just reverting the URL
                evt.stopImmediatePropagation();
                this.cancelNavigate = false;
                return;
            }
            if(this.activeController && this.activeController.isDirty && this.activeController.isDirty()) {
                var dialog = confirm("Any unsaved changes will be lost when you leave. Click Cancel to stay on the page, click OK to leave page.");
                if(dialog === true)
                    return;
                else {
                    evt.stopImmediatePropagation();
                    this.cancelNavigate = true;
                    window.location.href = evt.originalEvent.oldURL;
                }
            }
        },

        slugRoute: function(slug, feedType) {
            var userController = this.controllers['UserController'];
            if(!userController) {
                userController = new UserDetail();
            } 
            userController.loadUserFromSlug(slug, feedType)
        },

        modThis: function(e) {
            if(!suiteio.loggedInUser && suiteio.loggedInUser.get('isModerator')){ return; }     
            var adminController = this.controllers.AdminController;
            if(!adminController) {
                adminController = new AdminDetail({});
            }
            adminController.modThis(e);
        },

        adminRoute: function(viewType) {
            if (!suiteio.loggedInUser && !suiteio.loggedInUser.isStaff) {
                window.location.href = '/404';
                return;
            }
            var adminController = this.controllers.AdminController;
            if(!adminController) {
                adminController = new AdminDetail({});
            }
            switch(viewType) {
                case 'stats':
                    adminController.loadStatsView();
                break;
                default:
                    adminController.loadAdminMonitorView({
                        adminType: viewType
                    });
                break;
            }           
        }, 


        beforeUnload : function(e) {
            if(this.activeController && this.activeController.isDirty && this.activeController.isDirty()) {
                return 'Any unsaved changes will be lost if you leave or reload this page.';
            }
        }

    });
    return PageController;
});