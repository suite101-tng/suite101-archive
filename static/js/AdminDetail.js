// AdminDetail
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'views/AdminStatsView',
    'views/AdminMonitorView',
    'views/ModerateView'
], function(
    $,
    Backbone,
    _,
    suiteio,
    AdminStatsView,
    AdminMonitorView,
    ModerateView
) {
    'use strict';
    var AdminDetail = Backbone.View.extend({
        initialize: function(options) {
            options = options || {};
            this.id = 'AdminController';

            if(options.el) {
                this.setElement(options.el);
            }
            suiteio.pageController.registerController(this);
            this.listenTo(suiteio.pageController, 'closeDown-AdminController', function() {
                this.clearViews();
            });

         },

         modThis: function(e) {     
            var $target = $(e.currentTarget);
            var actionType = $target.data('mod-action') || '';
            var contentType = $target.data('type') || '';
            var contentId = $target.data('id') || '';
            var userId = $target.data('userid') || '';
            var moderator = suiteio.loggedInUser;

            console.log('content type is ' + contentType);
            this.clearViews();
            this.moderateView = new ModerateView({
                moderator: moderator
            });
            this.moderateView.openModCard({
                contentId: contentId,
                contentType: contentType
            });
            this.listenToOnce(this.moderateView, 'renderComplete', function() {
                this.moderateView.afterRender();
            });
         },

         loadStatsView: function() {
            var self = this;
            this.clearViews();

            this.statsView = new AdminStatsView({
            });

            this.listenToOnce(this.statsView, 'renderComplete', function($el) {
                // this.setupStorySupplementaryViews();
                // this.updateMeta();

                self.listenToOnce(suiteio.pageController, 'renderdone-'+self.id, function() {
                    self.statsView.loadChart();
                });

                self.trigger('pageChange', self, self.statsView.$el, '/admin/stats', {
                    trigger: false
                });
            });

            this.statsView.render();
          
        },

         loadAdminMonitorView: function(options) {
            options = options || {};
            var self = this;
            this.clearViews();
            var skipRender = options.skipRender || false;

            this.adminMonitorView = new AdminMonitorView(options);

            this.listenToOnce(this.adminMonitorView, 'renderComplete', function($el, url) {
                // this.setupStorySupplementaryViews();
                // this.updateMeta();

                self.listenToOnce(suiteio.pageController, 'renderdone-'+self.id, function() {
                    self.adminMonitorView.afterRender();
                });

                self.trigger('pageChange', self, self.adminMonitorView.$el, url, {
                    trigger: false
                });
            });
            if(!skipRender) {
                this.adminMonitorView.render();
            }
        },

        clearViews: function(views) {
            views = views || ['statsView', 'adminMonitorView', 'moderateView'];
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
            this.stopListening(this.statsView);
            this.statsView && this.statsView.destroy();
            this.statsView = null;
            Backbone.View.prototype.destroy.apply(this, arguments);
        }

    });
    return AdminDetail;
});    