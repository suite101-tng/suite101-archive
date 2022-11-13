/* globals define */
define([
    'jquery',
    'suiteio',
    'module',
    'backbone',
    'underscore',
    'NavDetail',
    'helpers/alertHandler',
    'helpers/KeyWatcher',
    'helpers/followMixin',
    'views/FlagView',
    'helpers/templateLoader',
    'main/PageController',
    'models/User',
    'helpers/MetaHandler',
    'hb',
    'lib/lazysizes',
    'helpers/jquery.placeholder',//noexports 
    'helpers/jquery.dynamicButtonHelper'//noexports 
],
function($,
    suiteio,
    module,
    Backbone,
    _,
    NavDetail,
    alertHandler,
    KeyWatcher,
    followMixin,
    FlagView,
    templateLoader,
    PageController,
    User,
    metaHandler
    //FooterView,
) {
    'use strict';
    // window.suiteio = suiteio;
    var settings = module.config();
    if(settings.loggedInUser) {
        suiteio.loggedInUser = new User.model(settings.loggedInUser);
    }
    var baseSearchURL = settings.baseSearchURL;
    var isPrivate = settings.isPrivate;

    suiteio.templateLoader = templateLoader;
    suiteio.staticUrl = settings.staticUrl;
    suiteio.metaHandler = metaHandler.initialize();

    //doc ready
    $(function () {
        suiteio.logDis = settings.logDis;
        suiteio.keyWatcher = new KeyWatcher();
        suiteio.notify = alertHandler.initialize();
        suiteio.pageController = new PageController();
        suiteio.navController = new NavDetail();
        $(window).on('beforeunload', function() {return suiteio.pageController.beforeUnload.apply(suiteio.pageController, arguments); });
        Backbone.history.start({
            pushState: true,
            root: '/',
            silent: true,
            hashChange: false
        });

        suiteio.fireLoginModal = function(join) {
            join = join || false;
            suiteio.navController.loadLoginModalView(join);
        };

        suiteio.canIContact = function(userId) {
               $.ajax({
                    url: '/u/api/contactable/' + userId,
                    type: 'POST',
                    data: {
                    },
                success: function(result) {
                    if(result=='True'){
                        return true;
                    } else {
                        return false;
                    } 
                }
            });
        };

        suiteio.acceptSuiteInvite = function(suite, accept) {
            if(!suiteio.loggedInUser) {
                suiteio.fireLoginModal();
                return;
            }
            var userId = suiteio.loggedInUser.id;
            var url = '/s/api/suite_invite_accept';
            $.ajax({
                url: url,
                type: 'POST',
                data: {
                    suite: suite,
                    user: userId,
                    accept: accept
                },
                success: function(status) {
                    // send this through the event bus to the requesting view
                    suiteio.vent.trigger('suiteInviteAccepted', status);
                }
            });
        },

        suiteio.followSuite = function(e) {    
            if(!suiteio.loggedInUser) {
                suiteio.fireLoginModal();
                return;
            }            
            var suiteId = $(e.currentTarget).data('suite');
            followMixin.followUnfollowAjax({
                e: e,
                followUrl: '/s/api/follow/'+ suiteId,
                unfollowUrl: '/s/api/unfollow/'+ suiteId
            });
        },

        suiteio.followUser = function(e) {    
            if(!suiteio.loggedInUser) {
                suiteio.fireLoginModal();
                return;
            }               
            var userId = $(e.currentTarget).data('user');
            console.log('user: ' +  userId);
            if(suiteio.loggedInUser.id===userId) {
                e.preventDefault();
                suiteio.notify.alert({
                     msg: 'Looks like you\'re trying to follow yourself!'
                 });
            } else {
                followMixin.followUnfollowAjax({
                    e: e,
                followUrl: '/u/api/follow/'+ userId,
                unfollowUrl: '/u/api/unfollow/'+ userId
                });
            }
        },

        suiteio.createSuiteModal = function(addingTo) {
            if(!suiteio.loggedInUser) {
                suiteio.fireLoginModal();
                return;
            }
            addingTo = addingTo || false;
            suiteio.navController.loadSuiteCreateView(addingTo);            
        };

        // suiteio.createNew = function() {
        //     this.pageController.createNewChat.apply(this.pageController, arguments);
        // };

        suiteio.flagIt = function(e) {            
            if(!suiteio.flagView) {
                suiteio.flagView = new FlagView({});
            } 
            suiteio.flagView.flagIt(e);
        };

        // suiteio.toggleFullTeaser = function(e) {
        //     var self = this;
        //     var $currentTarget = $(e.currentTarget);
        //     var $currentTeaser = $(e.currentTarget).closest('.storyTeaser');
        //     var storyTeaserTmplPromise = suiteio.templateLoader.getTemplate('story-teaser', ['tag-list-item']);   
        //     var postId = $currentTeaser.data('id');
        //     var postType = $currentTeaser.data('type');
        //     var full;

        //     var fetchFreshJson = function() {
        //         var url = '/a/api/full_teaser';
        //         return $.ajax({
        //             url: url,
        //             data: {
        //                 postid: postId,
        //                 posttype: postType,
        //                 full: full
        //             },
        //             type: 'POST'
        //         });
        //     };

        //     if($currentTeaser.hasClass('open')) {
        //         full = false;
        //     } else {
        //         full = true;
        //     }             

        //     fetchFreshJson().then(function(ctxt) {
        //         storyTeaserTmplPromise.done(function(tmpl) {
        //             var $html = tmpl(ctxt);
        //             $currentTeaser.replaceWith($html);

        //             switch(full) {
        //                 case true:
        //                     $currentTeaser.velocity('stop', true).velocity({ marginTop: 0, marginBottom: 0 }, {
        //                       duration: 120,
        //                       easing: [ 0.19, 1, 0.22, 1 ]
        //                     });  
        //                 break;
        //                 case false:
        //                     $currentTeaser.velocity('stop', true).velocity({ marginTop: 0, marginBottom: 0 }, {
        //                       duration: 120,
        //                       easing: [ 0.19, 1, 0.22, 1 ]
        //                     });  
        //                 break;
        //             }                    
        //         });
        //     }); 
        // };

        suiteio.eventRouter = function(eventData) {
             $.ajax({
                url: '/x/api/route_event',
                type: 'POST',
                data: eventData,
                success: function() {
                }
            });
        };

        suiteio.loadChatList = function(e) {
            if (!suiteio.loggedInUser) {
                suiteio.fireLoginModal();
                return;
            }
            var $currentTarget = $(e.currentTarget);
            suiteio.pageController.loadChatList()
        };

        suiteio.loadChat = function(e) {
            var $currentTarget = $(e.currentTarget);
            var hash = $currentTarget.data('hash');
            suiteio.pageController.loadChat(hash)
        };

        suiteio.checkUnread = function() {
            if (!suiteio.loggedInUser) {
                return;
            } else {
                return $.ajax({
                    type: "GET",
                    url: '/x/api/beacon',
                    success: function(response) {
                        if(response.beacon) {
                            $('.notifCount').html(response.beacon);
                            $('.notifsNav').addClass('hey');
                        } else { 
                            $('.notifsNav').removeClass('hey');
                        }
                    }
                });
            }
        };

        suiteio.getWindowSize = function() {
            var size = {
                width: window.innerWidth,
                height: window.innerHeight
            };
            return size;
        };

        suiteio.genericActionModal = function(options) {
            options = options || '';
            suiteio.navController.loadGenericActionModal(options);
        },

        suiteio.newConvModal = function(options) {
            options = options || '';
            suiteio.navController.loadNewConvModal(options);
        };

        suiteio.openSuiteSelector = function(e, create) {
            create = create || false;
            suiteio.navController.loadSuiteSelectorView(e, create);
        };


    });
});

