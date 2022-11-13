// GenericModalView
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
    var GenericModalView = Backbone.View.extend({
        events: function() {
            return _.extend({
                'hide.bs.modal': 'exit',
                'click .genericModalAction': 'passEvent'
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            var self = this;
            this.genericModalTmpl = suiteio.templateLoader.getTemplate('generic-action-modal');
            this.attrs = options || {};
            this.attrs.mainContent = options.mainContent;
            if(!this.attrs.act2) {
                this.attrs.act2 = {
                    action: 'godNo',
                    text: 'Cancel'
                };
            }
            this.listenToOnce(suiteio.vent, 'okToClose', function() {
                self.exit();
            });
        },
      
        render: function() {
            var self = this;
            var attrs = this.attrs;
            this.genericModalTmpl.done(function(tmpl) {
                self.genericModal = $(tmpl(attrs));
                self.genericModal.modal();
                self.setElement(self.genericModal);
            });
        },

        passEvent: function(e) {
            e.preventDefault;
            var $currentTarget = $(e.currentTarget);
            var persist = $currentTarget.data('persist') || false;
            var action = $currentTarget.data('action');
            suiteio.vent.trigger(action, e);  
            if(!persist) {
                this.genericModal.modal('hide');
            }
        },

        exit: function() {
            this.trigger('closeGenericModal');
        },

        destroy: function() {
            this.stopListening(suiteio.vent);
            Backbone.View.prototype.destroy.apply(this, arguments);
            this.unbind();
            this.$el.remove();
            this.remove();
        }


    });
    return GenericModalView;
});