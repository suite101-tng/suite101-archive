define([
    'jquery',
    'backbone',
    'underscore',
    'views/NavView',
    'views/DrawerView',
    'views/SuiteSelectorView',
    'views/LoginView',
    'views/SuiteCreateView',
    'views/GenericModalView',
    'suiteio'
], function(
    $,
    Backbone,
    _,
    NavView,
    DrawerView,
    SuiteSelectorView,
    LoginView,
    SuiteCreateView,
    GenericModalView,
    suiteio
) {
    'use strict';
    return Backbone.View.extend({
        initialize: function(options) {
            var _options = options || {};
            var self = this;
            this.id = 'NavController';
            suiteio.pageController.registerController(this);
            this.clearViews();
            this.navView = new NavView();
            
            this.listenTo(suiteio.pageController, 'pageChangeRenderDone', function($el) {
            });
            // this.listenTo(this.navView, 'fireNewStoryModal', function() {
            //     this.loadNewStoryModal({});
            // });        
            this.listenTo(this.navView, 'openDrawer', function() {
                self.openDrawer();
            });
        },

        openDrawer: function(tab) {
            var tab = tab || '';
            var self = this;
            this.clearViews(['drawerView']);
            this.drawerView = new DrawerView({});
            this.drawerView.openDrawer(tab);
            this.listenTo(this.drawerView, 'closeDrawer', function() {
                self.clearViews(['drawerView']);
            });
        },

        closeDrawer: function() {
            this.drawerView && this.drawerView.closeDrawer();
        },

        loadSuiteSelectorView: function(e, create) {
            console.log('loading suite selector');
            var self = this;
            create = create || false;
            var $currentTarget = $(e.currentTarget);
            var contentId = $currentTarget.data('id') || '';
            var contentType = $currentTarget.data('type');
            var contentTitle = $currentTarget.data('title');
            var activeTab = $currentTarget.data('tab');

            this.clearViews(['suiteSelectorView']);
            this.suiteSelectorView = new SuiteSelectorView({
                contentType: contentType,
                contentId: contentId,
                contentTitle: contentTitle,
                activeTab: activeTab,
                create: create
            });
            this.suiteSelectorView.openSelector();
            this.listenTo(this.suiteSelectorView, 'closeSuiteSelectorView', function() {
                self.clearViews(['suiteSelectorView']);
            });
        },     

        loadLoginModalView: function(join) {
            this.clearViews(['loginView']);
            this.loginView = new LoginView({
                join: join
            });
            var join = join || false;
            this.loginView.render();
            this.listenTo(this.loginView, 'closeLoginModal', function() {
                this.clearViews(['loginView']);
            });            
        },

        loadGenericActionModal: function(options) {
            this.clearViews(['genericModalView']);
            this.genericModalView = new GenericModalView(options)
            this.genericModalView.render();
            this.listenTo(this.genericModalView, 'closeGenericModal', function() {
                this.clearViews(['genericModalView']);
                suiteio.vent.trigger('genericModalClosed');  
            });              
        },

        loadSuiteCreateView: function(addingTo) {
            var addingTo = addingTo || false;
            this.clearViews(['suiteCreateView']);
            this.suiteCreateView = new SuiteCreateView({ addingTo: addingTo })
            this.suiteCreateView.render();
            this.listenTo(this.suiteCreateView, 'closeSuiteCreateModal', function() {
                this.clearViews(['suiteCreateView']);
            });             
        },

        // loadNewStoryModal: function(options) {
        //     console.log('loading new story modal...');
        //     var self = this;
        //     this.clearViews(['newStoryOptionsView']);
        //     this.newStoryOptionsView = new NewStoryOptionsView(options);
        //     this.listenTo(this.newStoryOptionsView, 'closeStoryModal', function() {
        //         this.clearViews(['newStoryOptionsView']);
        //     });
        //     this.newStoryOptionsView.openStoryCreateModal();
        // },   

        clearViews: function(views) {
            views = views || ['newStoryOptionsView', 'drawerView', 'navView', 'loginView', 'suiteSelectorView', 'suiteCreateView', 'genericModalView'];
            for(var view, i = 0, l = views.length ; i < l ; i += 1) {
                view = views[i];
                if(this[view]) {
                    this[view].destroy();                    
                    // this[view].unbind();
                    this.stopListening(this[view]);
                    this[view] = null;
                }
            }
        },

        getNavEl: function() {
            return this.navView.$el;
        }
    });
});