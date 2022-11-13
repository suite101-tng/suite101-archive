define([
    'backbone',
    'lib/underwood',
    'suiteio'], function(
    Backbone,
    Underwood,
    suiteio) {
    'use strict';
    return Backbone.View.extend({
        initialize: function(options) {
            options = options || {};
            this.user = suiteio.loggedInUser;
            this.id = options.id;
            this.attachTo = options.attachTo;
            this.templatePromise = suiteio.templateLoader.getTemplate('chat-reply-message');
        },

        render: function() {
            var self = this;
            var context = _.extend({msgId: this.id, currentUser: suiteio.loggedInUser.toJSON()});
            this.templatePromise.done(function(tmpl) {
                self.setElement(tmpl(context));
                self.attachTo.html(self.$el);
                self.$el.show(100);
                self.afterRender();
                self.trigger('renderdone', self.$el);
            });
        },

        close: function() {
            return this.$el.hide(100).promise();
        },

        destroy: function() {
            var self = this;
            this.close().done(function() {
                self.$el.remove();
            });
            Backbone.View.prototype.destroy.apply(this, arguments);
        },

        sendMessageReply: function(e) {
            var msg = this.$('.replyMsgBox').html();
            this.trigger('replyMessage', msg, this);
            $(e.currentTarget).dynamicButton({immediateEnable: true});
        },

        afterRender: function() {
            this.replyEditor = new Underwood(this.$('.replyMsgBox'), {
                buttons: [
                    'bold',
                    'italic',
                    'anchor'
                ]
            });
        }
    });
});