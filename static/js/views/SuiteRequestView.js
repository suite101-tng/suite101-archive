// SuiteRequestView
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'models/ChatMember',
    'lib/underwood'
], function(
    $,
    Backbone,
    _,
    suiteio,
    ChatMember,
    Underwood
    ) { 
    'use strict';
    var SuiteRequestView = Backbone.View.extend({
        events: function() {
            return _.extend({
                'click .showUserSettings': 'slideOpenUserTab',
                'click .showSettings': 'userTabGoodbye'

            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            var self = this;
            this.options = options;
            this.suite = this.options.suite;
            this.model = options.model;
            this.members = this.model.get('members'); // existing members, which we can glean from the model

            this.chatInviteModalTmplPromise = suiteio.templateLoader.getTemplate('chat-invite-modal');
            this.chatMemberTmplPromise = suiteio.templateLoader.getTemplate('chat-member-item');
            this.suiteUserSearchTmplPromise = suiteio.templateLoader.getTemplate('user-invite-item');
        },

        requestToJoin: function(e) {

            if(!suiteio.loggedInUser) { suiteio.fireLoginModal(); return; }

            var self = this;
            e.preventDefault();
            var $currentTarget = $(e.currentTarget);
            var userId = suiteio.loggedInUser.id;
            var suiteTitle = this.model.get('name');
            var suiteOwner = this.model.get('owner');
            var invited = this.model.get('viewerInvited') || false;
            var requested = this.model.get('viewerRequested') || false;
            var suiteId = this.model.id;
            console.log('invited? ' + invited);

            this.suiteRequestModalPromise.done(function(tmpl) {
                var $modal = $(tmpl({
                        alreadyInvited: invited,
                        alreadyRequested: requested,
                        placeholder: 'Type a brief message...',
                        owner: suiteOwner,
                        name: suiteTitle,
                        id: suiteId
                }));
                $modal.modal({expandIn: true, duration: 300});
                              
                $('.suiteRequestModal .msg').autoExpandTextarea();

                // $modal.on('click', '.submitBtn', function(e) {
                $modal.on('click', '.submitRequest', function(e, isRetry) {
                    if(!isRetry) {
                        $(e.currentTarget).dynamicButton({immediateEnable: true});
                    }
                    var message = $('.suiteRequestForm').find('.msg').val(),
                        $submit = $('.suiteRequestForm').find('.submitBtn').dynamicButton({immediateEnable: true});
                        self.submitRequestToJoin(userId, message, $modal);

                    $submit.dynamicButton('revert');
                    $modal.modal('hide');
                    $modal.remove();
                });

                $modal.on('click', '.acceptRejectInvite', function(e, isRetry) {
                    var accept = $(e.currentTarget).data('accept');
                    var suite = suiteId;
                    suiteio.acceptSuiteInvite(suiteId, accept);
                    self.listenToOnce(suiteio.vent, 'suiteInviteAccepted', function(status) {
                        // reload the page to clear everything...
                        window.location.reload(false);
                    });
                });
            });
        },

        submitRequestToJoin: function(user, message, $modal) {
            var self = this;
                $.ajax({
                    url: '/s/api/ask_to_join/' + this.model.id,
                    type: 'POST',
                    data: {
                        user: user,
                        suite: this.model.id,
                        msg: message
                    },
                success: function(result) {
                    var status = result.status;
                    if(result.status == "alreadyRequested") {
                            var message = 'Looks like you\'ve already asked to join this Suite. We\'ve resent the notification for you.'; 
                        } else { var message = 'Your request has been sent. We\'ll alert you as soon as you have a response.'; }
                       suiteio.notify.alert({
                            msg: message,
                            closeButton: true,
                            delay: 10000
                        });

                },
                error: function(response) {
                    suiteio.notify.alert({msg: 'There was a problem sending this request. Suite staff have been alerted. ', type: 'error'});
                }
            });
                
        },

        hide: function() {
            this.$el.hide();
        },

        show: function() {
            this.$el.show();
        },

        destroy: function() {
            this.$el.off('.searchuser');
            this.manageTitleEditor && this.manageTitleEditor.destroy();
            this.manageTitleEditor && this.manageDescEditor.destroy();
            $(document).off('.searchpeoplepane');
            Backbone.View.prototype.destroy.apply(this, arguments);
        }

    });
    return SuiteRequestView;

});