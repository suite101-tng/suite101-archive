define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'views/PagedListView',
    'helpers/ajaxFormErrorHandlerMixin'
], function(
    $,
    Backbone,
    _,  
    suiteio,
    PagedListView,
    ajaxFormErrorHandlerMixin
    ) {
    'use strict';
    var DrawerView = Backbone.View.extend({
        events: function() {
            return _.extend({
                'click .editPost': 'editPost'            
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            options = options || {};
            this.opened = false;
            this.scrollEl = this.$('.innerDrawerScroller');
            this.drawerThings = suiteio.templateLoader.getTemplate('drawer-things');
        },

        openDrawer: function(tab) {
            var self = this,
                tab = tab || '';
            this.closeOnClick = true;
            var size = suiteio.getWindowSize();                
            if(size.width && size.width > 1000) {
                this.closeOnClick = false;
            }              
            this.setElement($('.navDrawer'));
            $('.notifsContainer').removeClass('open');
            this.drawerWidth = this.getDrawerWidth();

            $('.navDrawer').velocity('stop', true).velocity({ bottom: 0 }, {
              duration: 140,
              easing: [ 0.035, 0.050, 1.000, -0.255 ]
            });

           $('.lowerLinks').velocity('stop', true).velocity({ bottom: 0 }, {
              duration: 160,
              delay: 140,
              easing: [ .12, .8, .22, .95 ]
            });

            $('.drawer').addClass('open');

            this.listenToOnce(suiteio.keyWatcher, 'keydown:27', this.closeDrawer);
            $('.shell').on('click', function() { self.closeDrawer(); });
            this.$('.thingsTab').on('click', function(e) { self.changeThingsTab(e); });
            this.$('a[data-navigate]').on('click', function(e) { self.linkCatcher(e); });
            

             $(document).off('.navDrawer .drawerScrollable');
             $(document).on('DOMMouseScroll mousewheel', '.navDrawer .drawerScrollable', function(ev) {
                var $this = $(this),
                    scrollTop = this.scrollTop,
                    scrollHeight = this.scrollHeight,
                    height = $this.height(),
                    delta = (ev.type == 'DOMMouseScroll' ?
                        ev.originalEvent.detail * -40 :
                        ev.originalEvent.wheelDelta),
                    up = delta > 0;

                var prevent = function() {
                    ev.stopPropagation();
                    ev.preventDefault();
                    ev.returnValue = false;
                    return false;
                }

                if (!up && -delta > scrollHeight - height - scrollTop) {
                    // Scrolling down, but this will take us past the bottom.
                    $this.scrollTop(scrollHeight);
                    return prevent();
                } else if (up && delta > scrollTop) {
                    // Scrolling up, but this will take us past the top.
                    $this.scrollTop(0);
                    return prevent();
                }
            });
            var wait = setTimeout(function() {   
                self.showMyThings();
            }, 200);
        },

         closeDrawer: function() {
            var self = this;            
            var size = suiteio.getWindowSize();
            var height = size.height;

            this.stopListening(suiteio.keyWatcher);

            $('.navDrawer').velocity('stop', true).velocity({ bottom: height }, {
              duration: 80,
              delay: 20,
              easing: [ 0.635, 0.000, 1.000, 0.725 ]
            });

           $('.lowerLinks').velocity('stop', true).velocity({ bottom: -64 }, {
              duration: 60,
              easing: [ .12, .8, .22, .95 ]
            });  

           $('.thingsTab').off('click');
           $('.editPost').off('click');
            var wait = setTimeout(function() { 
                $('.drawer').removeClass('open');
                self.trigger('closeDrawer');
             }, 160);
        },

        clearMyThings: function() {
            this.mySuitesListView && this.mySuitesListView.destroy();                
            $('.mySuites').find('.paginatedList').html('');            
        },

        getDrawerWidth: function() {    
            if(suiteio.getWindowSize().width < 480) {
                return suiteio.getWindowSize().width; } else { return 420; }
        },
 
        scrollBackUp: function() {
        console.log('scroll back up');
         this.$('.topLevel').velocity("scroll", { 
                container: this.scrollEl,
                  duration: 200,
                  offset: -80
                });

            // this.scrollEl.animate({scrollTop: this.scrollEl.position().top}, 200);

        },
       
        logMeOut: function() {
            if(!suiteio.loggedInUser) { return; }               
             $.ajax({
                url: '/logout',
                type: 'POST',
                data: {
                    authtype: 'logout'
                },
                success: function() {
                    console.log('logged you out!');
                    window.location.reload(false);
                }
            });
        },

        changeThingsTab: function(e) {
            console.log('tab change?');
            var tab = $(e.currentTarget).data('target');
            var tabName = tab.replace('#d-', '');
            this.showMyThings(tabName);
        },

        createNewSuite: function(e) {
            suiteio.createSuiteModal();
        },

        showMyThings: function(tabName) {
            var self = this;
            var $thingsContainer = this.$('.thingsContainer');
            tabName = tabName || 'suites';
            console.log('tab is now ' + tabName);
            var context = {};
            var listTemplate;
            var url = '/u/api/get_suites';
            switch(tabName) {
                case 'suites':
                    context.suites = true;
                    listTemplate = 'suite-mini-teaser';
                     url = '/u/api/get_suites';
                break
                case 'posts':
                    context.posts = true;
                    listTemplate = 'drawer-story-teaser';
                    url = '/u/api/get_posts';
                break     
                case 'people':
                    context.following = true;
                    listTemplate = 'user-teaser';
                    url = '/u/api/get_people';
                break         
            }

            this.drawerThings.done(function(tmpl) {
                var $html = $(tmpl(context));
                $thingsContainer.html($html);
                // switch(tabName) {
                //     case 'posts':
                //         $('.editPost').on('click', function(e) { console.log('hi, got your click!'); self.editPost(e); });
                //     break;
                // }
                                
                if(self.myThingsListView) {
                    self.myThingsListView && self.myThingsListView.destroy();
                }
                self.myThingsListView = new PagedListView({
                        firstPage: true,
                        scrollerEl: $('.drawerScrollable'),
                        el: $thingsContainer,
                        url: url,
                        templateName: listTemplate,
                        name: 'mythingslist'
                });
                self.listenTo(self.myThingsListView, 'listViewFiltered', function(namedFilter) {
                    namedFilter = namedFilter || '';
                    self.myThingsListView.fetch();
                });                     
                self.listenToOnce(self.myThingsListView, 'listViewReady', function() {
                    console.log('ready!');
                    self.myThingsListView.fetch();
                    $('.mySuites .paginatedList').velocity('stop', true).velocity('transition.fadeIn', 220);
                });
                self.listenToOnce(self.myThingsListView, 'errorFetchingCollection' || 'noListViewResults', function() {
                    console.log('No results');
                    self.$('.mySuites .paginatedList').html('');
                });
            });

        },

        loginModal: function() {
            var self = this;
            this.closeDrawer();
            suiteio.fireLoginModal();
        },

        linkCatcher: function() {
            console.log('link catcher!');
            if(this.closeOnClick) {
                this.closeDrawer();
            }
        },

        reactivateAccount: function(e) {

            var $target = $(e.currentTarget);
            var url = '/u/api/reactivate';

            var actionDecision = {};
            actionDecision.title = 'Activate your account';
            actionDecision.mainContent = '<p>Your account is currently inactive. You\'ll need to activate it (click below) to take part in discussions on Suite.</p>';
            actionDecision.act1 = {
                action: 'doActivateAccount',
                text: 'Activate'
            };
            this.listenTo(suiteio.vent, 'doActivateAccount', function() {
                $.ajax({
                    url: url,
                    type: 'POST',
                    data: {},
                    success: function() {
                        location.reload();
                    }
                });
            });                
            suiteio.genericActionModal(actionDecision);

            console.log('reactivating...');
            var $target = $(e.currentTarget),
                url = '/u/api/reactivate';

        },

        clearSupplementalViews: function() {
            var views = ['mySuitesListView'];
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
            console.log('destroying drawerview')
            this.stopListening();
            this.clearSupplementalViews();
            this.clearMyThings();
            this.unbind(); // Unbind all local event bindings
            $('.shell').off('click'); // Also unbind the shell click
        }

    });
    return DrawerView;
});



