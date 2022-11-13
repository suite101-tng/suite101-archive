    // StaticView
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'views/LoginView',
    'views/SupportView',
    'views/ArchiveView'
], function(
    $,
    Backbone,
    _,
    suiteio, 
    LoginView,
    SupportView,
    ArchiveView
) {
    'use strict';
    var StaticView = Backbone.View.extend({
        events: function() {
            return _.extend({
                    'click .discussThis': 'showStoryDiscussions',
                    'click .scrollToContent': 'scrollToContent'
                }, _.result(Backbone.View.prototype, 'events')
            );
        },
        initialize: function(options) {
            var self = this;
            options = options || {};
            this.options = options;
            this.feeds = {};
            this.viewType = options.viewType || '';
            this.subType = options.subType || '';
            this.rootUrl = options.rootUrl || '';
            var $el = $('#static-' + this.viewType);     
            console.log('viewtype is ' + this.viewType)       ;
            var template = 'static-shell';  
            switch(this.viewType) {
                case 'about':
                    template = 'static-about';
                break;
                case 'support':
                    template = 'support-shell', ['support-question'];
                break;   
                case 'archived':
                    template = 'archive-shell';
                break;                                
                case 'support':
                break;
                case 'auth':
                    template = 'static-auth';
                    $el = $('#static-' + this.subType);            
                break;
                case 'notfound':
                    template = 'static-notfound';
                    this.rootUrl = '/lib/api/notfound';
                break;
            }  

            this.templatePromise = suiteio.templateLoader.getTemplate(template,['support-question']);

            this.$('.tip').tooltip();

            if($el.length) {
                console.log('straight to afterRender()');
                this.setElement($el);
                this.afterRender();
            } else {
                console.log('el has no length....');
            }
        },

        fetchContext: function() {
            var self = this;
            return $.ajax({
                url: self.rootUrl,
                type: 'GET',
                data: {
                    spa: true,
                    viewtype: self.viewType
                }
            });
        },

        render: function() {
            var self = this;
            var $el;
            var $html;

            this.fetchContext().then(function(context) {
                self.templatePromise.done(function(tmpl) {
                    if(self.viewType == 'login') {
                        var ctxt = context;
                        context = $.extend(ctxt, {csrf: suiteio.csrf});
                    }
                    $html = $(tmpl(context));
                    // self.$el.html($html);
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
            console.log('viewtype is ' + this.viewType);
            if(this.viewType) {
                switch(this.viewType) {
                case 'auth':
                    this.setupLoginView();
                break;
                case 'support':
                    this.setupSupportView();
                break;                
                case 'archived':
                    this.setupArchiveView();
                break;
                case 'about':
                    this.loadConvState();
                    var regBut = '<div class="btn btn-blueTranslucent home-login-butt createAccount" data-actionbind="createAccount">Create an account</div>';
                    if(!suiteio.loggedInUser) {
                        this.$('.trailingStaticReg').html(regBut);
                    } 
                break;                                    
                }
            }
        },

        setupArchiveView: function() {
            console.log('setting up supportView');
            var self = this;
            this.clearAllMainViews();
            this.archiveView = new ArchiveView({
                el: self.$el,
            });            
        },

        setupSupportView: function() {
            console.log('setting up supportView');
            var self = this;
            this.clearAllMainViews();
            this.supportView = new SupportView({
                el: self.$el,
            });            
        },

        loadConvState: function() {
            this.$('.avatarPromo0 .profileImage').velocity('stop', true).velocity({ scale: [1, 1.4] }, {
              duration: 800,
              easing: [ .12, .8, .22, .95 ]
            });
            this.$('.avatarKids').velocity('stop', true).velocity({ opacity: 1 }, {
              delay: 200,
              duration: 200,
              easing: [ .12, .8, .22, .95 ]
            });
            // if x is less than width of container, we manipulate svg line's x1 property; else x2... etc
            this.$('#avline1').velocity('stop', true).velocity({ x2:400, y2:340 }, {delay: 100, duration: 300, easing: [ .12, .8, .22, .95 ] });
            this.$('#avline2').velocity('stop', true).velocity({ x2:420, y2:48 }, {delay: 200, duration: 300, easing: [ .12, .8, .22, .95 ] });
            this.$('#avline3').velocity('stop', true).velocity({ x2:24, y2:128 }, {delay: 300, duration: 300, easing: [ .12, .8, .22, .95 ] });
            this.$('#avline4').velocity('stop', true).velocity({ x2:90, y2:84 }, {delay: 400, duration: 300, easing: [ .12, .8, .22, .95 ] });
            this.$('#avline5').velocity('stop', true).velocity({ x2:130, y2:360 }, {delay: 400, duration: 300, easing: [ .12, .8, .22, .95 ] });
            this.$('#avline6').velocity('stop', true).velocity({ x2:290, y2:340 }, {delay: 400, duration: 300, easing: [ .12, .8, .22, .95 ] });

            this.$('.avatarPromo1').velocity('stop', true).velocity({ left: 400, top: 340 }, { delay: 100, duration: 100, easing: [ .12, .8, .22, .95 ] });
            this.$('.avatarPromo2').velocity('stop', true).velocity({ left: 420, top: 48 }, { delay: 200, duration: 100, easing: [ .12, .8, .22, .95 ] });            
            this.$('.avatarPromo3').velocity('stop', true).velocity({ left: 24, top: 128 }, { delay: 300, duration: 100, easing: [ .12, .8, .22, .95 ] });                        
            this.$('.avatarPromo4').velocity('stop', true).velocity({ left: 90, top: 84 }, { delay: 400, duration: 100, easing: [ .12, .8, .22, .95 ] });                     
            this.$('.avatarPromo5').velocity('stop', true).velocity({ left: 130, top: 360 }, { delay: 400, duration: 100, easing: [ .12, .8, .22, .95 ] });                     
            this.$('.avatarPromo6').velocity('stop', true).velocity({ left: 290, top: 340 }, { delay: 400, duration: 100, easing: [ .12, .8, .22, .95 ] });                     
        },

        setupLoginView: function() {
            console.log('setting up loginview');
            var self = this;
            this.clearAllMainViews();
            this.loginView = new LoginView({
                el: self.$el,
                loginMode: this.subType,
                authUrl: this.rootUrl
            });
        },

        createAccount: function(e) {
            suiteio.fireLoginModal();
        },

        clearAllMainViews: function() {
            var views = ['loginView', 'supportView', 'archiveView'];
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
            this.clearAllMainViews();
            Backbone.View.prototype.destroy.apply(this, arguments);
        }
    });

    return StaticView;
});