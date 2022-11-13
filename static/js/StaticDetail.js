// StaticDetail
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'views/StaticView'
], function(
    $,
    Backbone,
    _,
    suiteio,
    StaticView
) {
    'use strict';
    var StaticDetail = Backbone.View.extend({
        initialize: function(options) {
            options = options || {};
            this.id = 'StaticController';

            if(options.el) {
                this.setElement(options.el);
            }
            suiteio.pageController.registerController(this);
            this.listenTo(suiteio.pageController, 'closeDown-StaticController', function() {
                this.clearAllMainViews();
            });

         },

         loadStaticView: function(options) {
            var self = this;
            var rootUrl;

            this.viewType = options.viewType || '';
            this.subType = options.subType || '';

            if(this.viewType == 'auth') {
                rootUrl = '/' + this.subType;    
            } else {
                rootUrl = '/' + this.viewType;
            }

            var skipRender = options.skipRender || false;
            if(this.viewType=="notfound") {
                this.notfound = true;
            }
            this.clearAllMainViews();

            this.staticView = new StaticView({
                viewType: self.viewType,
                subType: self.subType,
                rootUrl: rootUrl
            }); // need to pass in options with path data

            this.listenToOnce(self.staticView, 'renderComplete', function($el) {
                console.log('static after render');
                // this.setupStorySupplementaryViews();
                // this.updateMeta();
                self.listenToOnce(suiteio.pageController, 'renderdone-'+self.id, function() {
                    console.log('renderdone');
                    this.staticView.afterRender();
                });

                if(!self.notfound) {
                    self.trigger('pageChange', self, self.staticView.$el, rootUrl, {
                        trigger: false
                    });
                } else { 
                        console.log('notfound pagechange');
                        self.trigger('pageChange', self, self.staticView.$el, '', {
                        trigger: false,
                        replace: true
                    });
                 }
            });
            if(!skipRender) {
                this.staticView.render();
            } 
        },

        clearAllMainViews: function() {
            var views = ['staticView'];
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
            this.stopListening(this.staticView);
            this.staticView && this.staticView.destroy();
            this.staticView = null;
            Backbone.View.prototype.destroy.apply(this, arguments);
        }

    });
    return StaticDetail;
});