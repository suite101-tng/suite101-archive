// FlagView
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'lib/underwood'
], function(
    $,
    Backbone,
    _,
    suiteio,
    Underwood
    ) {
    'use strict';
    var FlagView = Backbone.View.extend({
        el: '[data-view-bind="FlagView"]',
        events: function() {
            return _.extend({
                // 'click .modUserDetail': 'fetchUserData'
            }, _.result(Backbone.View.prototype, 'events'));
        },
        initialize: function (options) {
            this.flagModalPromise = suiteio.templateLoader.getTemplate('flag-modal');
            this.options = options || '';
        },


        flagIt: function(e) {
            var self = this;
            var $currentTarget = $(e.currentTarget);
            this.contentId = $currentTarget.data('id');
            this.contentType = $currentTarget.data('type');

            if(!suiteio.loggedInUser) { suiteio.fireLoginModal(); return; }

            switch(this.contentType) {
                case 'story':
                    self.flagUrl = '/a/api/flag'
                break;
                case 'link':
                    self.flagUrl = '/l/api/flag'
                break;
                case 'message':
                    self.flagUrl = '/m/api/flag'
                break;
                case 'suite':
                    self.flagUrl = '/s/api/flag'
                break;                                
                case 'user':
                    self.flagUrl = '/u/api/flag'
                break;            
            }

            this.flagModalPromise.done(function(tmpl) {
                self.flagModal = $(tmpl({
                        instruction: '',
                        thing: self.contentType
                }));
                self.flagModal.modal({ expandIn: true });
                self.setElement($('.flagModal'));

                self.flagEditor = new Underwood(self.$('.flagMessage'), {
                    toolbar: false, 
                    spellcheck: false,                 
                    placeholder: {
                        hideOnClick: false,
                        text: 'Type a note to explain what\'s wrong'
                    },                       
                })  

                                    
                // $modal.on('click', '.flagSubmitBtn', function() {
                //     console.log('submitted!');
                //     var flagData = {
                //         flagcontentid: contentId,
                //         message: $('.flagMessage').val()
                //         },
                //         var $submit = $('.flagSubmitBtn').dynamicButton({immediateEnable: true});
                //         if(!flagData.message) {
                //             suiteio.notify.alert({
                //                 msg: 'Please tell us why you\'re reporting this.',
                //                 delay: 3000
                //             });
                //             $submit.dynamicButton('revert');
                //             return;
                //         }
                    
                //         self.submitFlag(flagData, $modal);

                //     $submit.dynamicButton('revert');
                //     $modal.modal('hide');
                //     $modal.remove();
                // });
            });
        },

        submitFlag: function(flagData, $modal) {
            var self = this;
            var $submit = $('.flagSubmitBtn').dynamicButton({immediateEnable: true});
            var flagData = {
                flagcontentid: self.contentId,
                contenttype: self.contentType,
                message: $('.flagMessage').html()
                }
            var $submit = $('.flagSubmitBtn').dynamicButton({immediateEnable: true});
                if(!flagData.message) {
                    suiteio.notify.alert({
                        msg: 'Please tell us why you\'re reporting this.',
                        delay: 3000
                    });
                    $submit.dynamicButton('revert');
                    return;
                }

                 $.ajax({
                    url: self.flagUrl,
                    type: 'POST',
                    data: flagData,
                success: function() {

                
                    $submit.dynamicButton('revert');
                    self.flagModal.modal('hide');
                    self.flagModal.remove();

                       suiteio.notify.alert({
                            msg: 'Thanks for reporting. We\'ll take a look, and get back to you if we have any questions.',
                            delay: 4000
                        });

                },
                error: function(response) {
                    suiteio.notify.alert({msg: 'Something went wrong reporting this. Suite staff have been alerted. ', type: 'error'});
                }
            });
                
        },

        destroy: function() {
            this.flagEditor && this.flagEditor.destroy();
            Backbone.View.prototype.destroy.apply(this, arguments);
        }


    });
    return FlagView;
});