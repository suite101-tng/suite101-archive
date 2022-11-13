//LinkDetail
define([
    'jquery',
    'backbone',
    'models/Link',
    'views/LinkView',
    'suiteio'
], function(
    $,
    Backbone,
    Link,
    LinkView,
    suiteio
    
) {
    'use strict';
    var LinkController = Backbone.View.extend({

        initialize: function(options) {
            var model;
            this.options = options;
            this.id = 'LinkController';

            suiteio.pageController.registerController(this);
            suiteio.pageController.registerEventBroadcast([
                // 'respondedToLink',
            ], this);
            this.listenTo(suiteio.pageController, 'closeDown-LinkController', function() {
                this.clearViews();
            });
            // this.listenToOnce()
        },

        updateMeta: function(linkModel) {
            var attrs = {};
            if(!linkModel) {
                attrs = {
                    'title': 'External Link',
                    'removeMeta': [{
                        'name': 'author'
                    },
                    {
                        'name': 'copyright'
                    }]
                };
            } else {
                attrs = {
                    'title': 'just a test title',
                    'meta': [{
                        'name': 'owner',
                        'content': ''
                    }]
                };
            }
            suiteio.metaHandler.updateHead(attrs);
        },

        fetchContext: function() {
            return $.ajax({
                url: this.rootUrl,
                type: 'GET',
                data: {
                    spa: true
                }
            });
        },

         loadLinkView: function(options) {
            var self = this;
            options = options || {};
            var skipRender = options.skipRender || false;
            this.clearViews();
            this.linkView = new LinkView(options);

            this.listenToOnce(this.linkView, 'renderComplete', function($el) {
                // this.setupStorySupplementaryViews();
                // this.updateMeta();

                self.listenToOnce(suiteio.pageController, 'renderdone-'+self.id, function() {
                    self.linkView.afterRender();
                });

                console.log('render complete!');
                self.trigger('pageChange', self, self.linkView.$el, '', {
                    trigger: false
                });
            });
            if(!skipRender) {
                console.log('we should be rendering if that was an SPA action');
                this.linkView.render();
            }
        },

        clearViews: function(views) {
            views = views || ['linkView'];
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
            suiteio.pageController.unregisterRouter(this);
            this.stopListening();
            this.detailView && this.detailView.destroy();
        }
    });
    return LinkController;
});