//StoryView.js
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
    var StoryView = Backbone.View.extend({

        events: function() {
            return _.extend({
                'click .dateTime': 'toggleDates'
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            var self = this;
            this.templateName = 'story-detail';
            this.needForceRender = false;
            this.templatePromise = suiteio.templateLoader.getTemplate(this.templateName, [
                'story-embed',
                'story-parent',
                'tag-list-item'
            ]);
            this.ownerViewing = false;
            this.model = options.model;

            this.bootstrapped = options.bootstrapped || false;

            if(!this.bootstrapped) { //SPA, expect model to sync
                this.listenToOnce(this.model, 'sync', function() {
                    self.ownerViewing = !!(suiteio.loggedInUser && (suiteio.loggedInUser.id == self.model.get('author').id));
                    self.render();
                });
            } else {
                var $el = $('.pageContainer#story-'+this.model.id);
                if($el.length) {
                    this.setElement($el);
                } else {
                    this.needForceRender = true;
                }                
            }

            this.isMod = suiteio.loggedInUser && suiteio.loggedInUser.get('isModerator');          

        },

        render: function() {
            var self = this;
            this.templatePromise.done(function(tmpl) {
                var contextMixin = {
                    clientSideRender: true,
                    userLoggedIn: !!(suiteio.loggedInUser && (suiteio.loggedInUser.id)),
                    ownerViewing: self.ownerViewing,
                    isMod: self.isMod
                },
                    context = {},
                    $html,
                    $el;
                if(suiteio.loggedInUser) {
                    contextMixin.loggedInUser = suiteio.loggedInUser.toJSON();
                }
                context = $.extend(contextMixin, self.model.toJSON());
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
                self.needForceRender = false;
            });
        },

        afterRender: function() {
            var self = this;
            this.$('.tip').tooltip();
         },

        toggleDates: function(e) {
            this.$('.dateTime').toggleClass('mod');
        },

        ////// TODO: get selected text, use in tweet, share, etc
        // shareFromSelection: function() {
        //     var html = "";
        //     if (typeof window.getSelection != "undefined") {
        //         var sel = window.getSelection();
        //         if (sel.rangeCount) {
        //             var container = document.createElement("div");
        //             for (var i = 0, len = sel.rangeCount; i < len; ++i) {
        //                 container.appendChild(sel.getRangeAt(i).cloneContents());
        //             }
        //             html = container.innerHTML;
        //         }
        //     } else if (typeof document.selection != "undefined") {
        //         if (document.selection.type == "Text") {
        //             html = document.selection.createRange().htmlText;
        //         }
        //     }
        //     return html;
        // },

        destroy: function() {
            Backbone.View.prototype.destroy.apply(this, arguments);
        }

    });
    return StoryView;
});