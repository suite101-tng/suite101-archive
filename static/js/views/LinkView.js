//LinkView
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio'
], function(
    $,
    Backbone,
    _,
    suiteio
) {
    'use strict';
    var LinkView = Backbone.View.extend({
        events: function() {
            return _.extend({
                    'click .scrollToContent': 'scrollToContent'
                }, _.result(Backbone.View.prototype, 'events')
            );
        },
        initialize: function(options) {
            var self = this;
            options = options || {};
            this.model = options.model || '';
            var linkId = options.id || options.model.id;

            var hashedId = options.hash || this.model.hash;
            this.rootUrl = '/l/' + hashedId;

            this.templatePromise = suiteio.templateLoader.getTemplate('link-shell', ['story-teaser']);
            var $el = $('.pageContainer#link-'+linkId);

            if($el.length) {
                this.setElement($el);
                this.trigger('renderComplete');
                this.afterRender();
            } else {
                // this.render();
            }            
        },

        fetchContext: function() {
            var self = this;
            return $.ajax({
                url: self.rootUrl,
                type: 'GET',
                data: {
                    spa: true
                }
            });
        },

        render: function() {
            var self = this;
            var $el;
            var $html;
            this.fetchContext().then(function(context) {
                console.log(context);
                self.templatePromise.done(function(tmpl) {
                    $html = $(tmpl(context));
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
                    // self.setupLazyLoader();
                });      
            });
        },     

        afterRender: function() {
            // suiteio.setupMainInlineCreate({
            //     parentId: this.model.id,
            //     container: self.$('.mainResponseBlock'),
            //     type: 'link'
            // });
        },
        
        openSuiteSelector: function(e) {
            suiteio.openSuiteSelector(e);
        },
        
        destroy: function() {
            Backbone.View.prototype.destroy.apply(this, arguments);
        }
    });

    return LinkView;
});