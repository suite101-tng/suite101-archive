define([
    'jquery',
    'backbone',
    'underscore',
    'views/UserView',
    'views/UserEditView',
    'views/UserSettingsView',
    'views/NotificationsView',
    'views/StatsView',
    'models/User',
    'suiteio'
],
function(
    $,
    Backbone,
    _,
    UserView,
    UserEditView,
    UserSettingsView,
    NotificationsView,
    StatsView,
    User,
    suiteio
) {
    'use strict';
    var UserController = Backbone.View.extend({

        initialize: function(options) {
            options = options || {};                        
            var self = this;
            this.id = 'UserController';
            suiteio.pageController.registerController(this);
            this.collection = new User.collection();

            this.listenTo(suiteio.pageController, 'closeDown-UserController', function() {
                if(self.notifsView) {
                    self.updateReadNotifs();
                }
                this.clearViews();
            });
        },

        loadSettingsView: function(options) {
            console.log('welcome to loadSettingsView');
            var self = this;
            var skipRender = options.skipRender || false;
            var settingsData = options.settingsData || '';
            console.log('hi, we have settings data');
            console.log(settingsData);  
            
            var metaAttrs = {
                title: 'Settings',
                meta: [{
                    'name': 'description',
                    'content': 'Configure your profile, privacy and other details.'
                }]
            };
            
            this.clearViews();
            this.settingsView = new UserSettingsView({
            });

            this.listenToOnce(this.settingsView, 'renderComplete', function($el) {
                self.settingsView.afterRender();
                this.updateMeta(metaAttrs);

                self.listenToOnce(suiteio.pageController, 'renderdone-'+self.id, function() {
                });

                self.trigger('pageChange', self, self.settingsView.$el, '/settings', {
                    trigger: false
                });
            });
            if(!skipRender) {
                this.settingsView.render();
            } else {
                this.settingsView.settingsData = settingsData;
                this.settingsView.afterRender();
            }          
        },

        loadBootstrappedUser: function(options) {
            var self = this;
            var bootstrappedModel = options.bootstrappedModel || {};
            bootstrappedModel = new User.model(bootstrappedModel);
            this.collection.add(bootstrappedModel);
            bootstrappedModel.fetch().done(function() {
                self.collection.add(bootstrappedModel);
                self.loadUserView(bootstrappedModel, {bootstrapped: true, feedType: options.feedType});
            });
        },

        loadUserFromSlug: function(slug, feedType) {
            console.log('trying to load from slug... (' + slug + ')');
            var self = this;
            var model = this.collection.findWhere({slug: slug});
            this.haveBootstrappedUser = false;
            if(!model) {
                console.log('no model; let\'s fetch one');
                model = new User.model({slug: slug});
                model.fetch().done(function(newUserModel) {
                    self.collection.add(newUserModel);
                    console.log(newUserModel);
                });
            } 
            this.loadUserView(model, {
                bootstrapped: self.haveBootstrappedUser,
                feedType: feedType
            });
        },

        loadUserView: function(model, options) {
            var href = null;
            var metaAttrs = {
                title: model.get('fullName'),
                meta: [{
                    'name': 'description',
                    'content': model.get('byLine')
                }]
            };          
            this.clearViews();
            this.userView = new UserView({
                model: model,
                bootstrapped: options.bootstrapped,
                feedType: options.feedType
            });
            this.userModel = model;
            if(!options.bootstrapped) {//SPA load
                this.trigger('pageLoading');
                this.listenTo(this.userView, 'renderComplete', function($el) {
                    if(options.refreshHref) { href = model.get('absoluteUrl');}
                    this.updateMeta(metaAttrs);
                    this.trigger('pageChange', this, $el, href, {trigger: false});
                    this.userView.afterRender();
                });
                model.fetch({
                    error: function() {
                        suiteio.pageController.notFound();
                    }
                });
            } else {//fresh page load || visited
                if(options.refreshHref) { href = model.get('absoluteUrl');}
                this.updateMeta(metaAttrs);
                this.trigger('pageChange', this, this.userView.$el, href, {trigger: false});
                this.userView.afterRender();
            }
            this.listenToOnce(this.userView, 'openEditMode', function(model) {
                this.startEditMode(true, model);
            });
            this.listenTo(this.userView, 'tabChange', function(url) {
                suiteio.pageController.navigate(url, {trigger: false, replace: true});
            });
        },


        startEditMode: function(bootstrapped, model) {
            if(suiteio.loggedInUser.id !== model.id && !suiteio.loggedInUser.get('isStaff') && !suiteio.loggedInUser.get('isModerator')) {
                //not the owner, nor mod, nor staffer
                return;
            }
            if(this.userView) {
                this.userView.destroy();
                this.userView = null;
            }
            if(this.userEditView) {
                this.userEditView.destroy();
            }
            this.userEditView = new UserEditView({
                bootstrapped: bootstrapped,
                model: model
            });
            this.listenToOnce(this.userEditView, 'doneEditMode', this.doneEditMode);
        },

        // NOTIFICATIONS
         loadNotificationsView: function(options) {
            var self = this;
            options = options || {};
            var skipRender = options.skipRender || false;
            var metaAttrs = {
                title: 'Notifications',
                meta: [{
                    'name': 'description',
                    'content': 'Notifications and special announcements just for you.'
                }]
            };            
            this.clearViews();
            if(!suiteio.loggedInUser) {
                suiteio.fireLoginModal();
                return;
            }
            this.notifsView = new NotificationsView({
            });            
            this.listenToOnce(self.notifsView, 'renderComplete', function($el) {
                // this.setupStorySupplementaryViews();
                this.updateMeta(metaAttrs);

                self.listenToOnce(suiteio.pageController, 'renderdone-'+self.id, function() {
                    self.notifsView.afterRender();
                });

                self.trigger('pageChange', self, self.notifsView.$el, '', {
                    trigger: false
                });
            });
            if(!skipRender) {
                this.notifsView.render();
            }
        },        

        updateReadNotifs: function() {
            $.ajax({
                url: '/notifications',
                type: 'POST',
                data: {
                    readem: true
                },
                success: function() {
                }
            });
        },

        // USER STATS
        loadStatsView: function() {
            var self = this;
            this.clearViews();
            var metaAttrs = {
                title: 'Stats',
                meta: [{
                    'name': 'description',
                    'content': 'All my Suite stats.'
                }]
            };
            this.statsView = new StatsView({
            });

            this.listenToOnce(this.statsView, 'renderComplete', function($el) {
                // this.setupStorySupplementaryViews();
                this.updateMeta(metaAttrs);

                self.listenToOnce(suiteio.pageController, 'renderdone-'+self.id, function() {
                    self.statsView.loadChart();
                });

                self.trigger('pageChange', self, self.statsView.$el, '/stats', {
                    trigger: false
                });
            });

            this.statsView.render();
          
        },

        updateMeta: function(attrs) {
            suiteio.metaHandler.updateHead(attrs);
        },

        isDirty: function() {
            return false;//for now...
        },

        clearViews: function(views) {
            views = views || ['settingsView', 'userEditView', 'userView', 'statsView', 'notifsView'];
            for(var view, i = 0, l = views.length ; i < l ; i += 1) {
                view = views[i];
                if(this[view]) {
                    this[view].destroy();
                    this.stopListening(this[view]);
                    this[view] = null;
                }
            }
        },

        doneEditMode: function(model) {
            this.userEditView && this.userEditView.destroy();
            this.userEditView = null;
            if(model) {
                this.trigger('editedUser', model); //announce it, see if anyone cares
                this.loadUserView(model, {bootstrapped: true, forceRender: true, refreshHref: true});
            }
        }

    });
    return UserController;
});