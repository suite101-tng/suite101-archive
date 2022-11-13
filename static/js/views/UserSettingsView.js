// UserSettingsView
define([
    'jquery',
    'backbone',
    'suiteio',
    'dropzone',
    'lib/underwood',
    'helpers/ajaxFormErrorHandlerMixin'
],
function(
    $,
    Backbone,
    suiteio,
    Dropzone,
    Underwood,
    ajaxFormErrorHandlerMixin
) {
    'use strict';
    var UserSettingsView = Backbone.View.extend({
        
        events: function() {
            return _.extend({
                
                'submit .emailEditForm': 'submitEmailChange',
                'submit .gaSettingsForm': 'gaSettingsForm',
                'submit .emailSettingsForm': 'submitEmailSettingsChange',
                'keyup .settingUserSlug': 'slugKeyHandler',
                'keyup .settingUserGaCode': 'gaCodeKeyup',
                'keyup .profileSettings .profileField': 'profileFieldKeyup',

                
                'click .unlinkTwitter': 'unlinkTwitter',
                'click .dloadStories': 'downloadMyStories',
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function () {
            var self = this;
            // this.$el = $('.notifsContainer');
            // this.setElement($('.notifsContainer'));
            this.templatePromise = suiteio.templateLoader.getTemplate('settings-shell');

            this.rootUrl = '/settings';
            this.settingsEditors = {};
            this.editorEls = ['settingUserName', 'settingUserByline', 'settingUserWebsite', 'settingUserLocation', 'settingUserSlug', 'settingUserGaCode'];

            var $el = $('#settings-view');
            // $el.find('.tip').tooltip('destroy').tooltip();
            if($el.length) {
                this.setElement($el);
                this.trigger('renderComplete');
            } else {
                /////
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
                self.settingsData = context;
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
                });      
            });
        },

        afterRender: function() {
            console.log(this.settingsData);
            this.setupSettingsEditors();            
        },

        setupSettingsEditors: function() {
            var self = this;
            console.log('set up editors');
            var eds = this.editorEls;        

            for(var ed, i = 0, l = eds.length ; i < l ; i += 1) {
                ed = eds[i];
                self.settingsEditors[ed] = new Underwood(self.$('.' + ed), {
                    toolbar: false,
                    disableReturn: true,   
                    spellcheck: false,                 
                    placeholder: {
                        hideOnClick: false,
                        text: ''
                    },                       
                });  
            }
        },

        destroySettingsEditors: function() {
            var self = this;
            var eds = this.editorEls;  
            for(var ed, i = 0, l = eds.length ; i < l ; i += 1) {
                ed = eds[i];
                self.settingsEditors[ed] && self.settingsEditors[ed].destroy();
            }
            this.settingsEditors = void 0;
        },

        saveUserAttrs: function(attrs, confirm) {
            var confirm = confirm || false;
            suiteio.loggedInUser.save(attrs, {
                wait: true,
                success: function() {
                    if(confirm) {
                        suiteio.notify.alert({ msg: 'Saved', delay: 30000 });
                    }
                    return true;
                },
                error: function(model, resp) {
                    var type = 'error',
                        msg = 'Oops! Something went wrong; please try again.';
                    suiteio.notify.alert({
                        type: type,
                        msg: msg
                    });
                    return false;
                }
            });
        },

        closeAccount: function(e) {
            var self = this;
            var $target = $(e.currentTarget);
            var url = '/u/api/delete';

            var actionDecision = {};
            actionDecision.title = 'Close your account';
            actionDecision.mainContent = '<p>Clicking the button below will delete your posts and close up your profile.</p><p>If you\'ve not already done so, and need to, <span class="genericModalAction inline-linklike" data-persist="true" data-actionbind data-action="doExportStories">download a backup copy of your stories</span>.</p>';

            actionDecision.act1 = {
                action: 'doCloseAccount',
                text: 'Close account'
            };
           
            this.listenTo(suiteio.vent, 'doExportStories', self.downloadMyStories());

            this.listenTo(suiteio.vent, 'doCloseAccount', function() {
                $.ajax({
                    url: url,
                    type: 'POST',
                    data: {},
                    success: function() {
                        location.reload();
                    }
                });
            });                
            suiteio.genericActionModal(actionDecision);
        },

        deactivateAccount: function(e) {
            var $target = $(e.currentTarget);
            var url = '/u/api/deactivate';

            var actionDecision = {};
            actionDecision.title = 'Deactivate your account';
            actionDecision.mainContent = '<p>You will still be able to access your account, but your profile will no longer be visible to the public. You can re-activate anytime you like.</p>';
            actionDecision.act1 = {
                action: 'doDeactivateAccount',
                text: 'Deactivate'
            };
            this.listenTo(suiteio.vent, 'doDeactivateAccount', function() {
                $.ajax({
                    url: url,
                    type: 'POST',
                    data: {},
                    success: function() {
                        location.reload();
                    }
                });
            });                
            suiteio.genericActionModal(actionDecision);
        },

        reactivateAccount: function(e) {
            console.log('reactivating...');
            var $target = $(e.currentTarget),
                url = '/u/api/reactivate';

            suiteio.notify.prompt({
                msg: 'Activate your account?',
                yes: 'Yes',
                no: 'No'
                }).done(function(decision) {
                if(decision) {
                    $.ajax({
                        url: url,
                        type: 'POST',
                        data: {},
                        success: function() {
                            // $('.modFeature').toggleClass('featured green');
                        suiteio.notify.alert({
                            msg: 'You\'re active!'
                        });
                        location.reload();
                        }
                    });
                }
            });
        },

        submitEmailChange: function(e) {
            e.preventDefault();
            var $form = $(e.currentTarget),
                postData = $form.serialize(),
                self = this,
                $updateEmailBtn = this.$('.updateEmailBtn').dynamicButton({immediateEnable:true});
            return $.ajax({
                url: '/profile/email/change',
                dataType: 'json',
                type: 'POST',
                data: postData,
                success: function() {
                    suiteio.notify.alert({
                        msg: $form.find('.emailUpdateSuccess').val(),
                        type: 'success',
                        delay: -1
                    });
                },
                error: function() {
                    self.formErrorHandler.apply(self, arguments);
                }
            }).always(function() {
                $updateEmailBtn.dynamicButton('revert');
            });
        },

        submitPasswordChange: function(e) {
            console.log('submitPasswordChange');
            e.preventDefault();
            var pw = this.$('#settings_pw').val();
            var pw2 = this.$('#settings_pw2').val();

            console.log(pw + ', ' + pw2);

            if(pw!=pw2) {            
                suiteio.notify.alert({
                    msg: 'Passwords don\'t match!',
                    type: 'success',
                    delay: -1
                });
                return;
            }
            var $updatePasswordBtn = this.$('.updatePasswordBtn').dynamicButton({immediateEnable:true});

            return $.ajax({
                url: self.rootUrl,
                dataType: 'json',
                type: 'POST',
                data: {
                    changepw: true,
                    pw: pw
                },
                success: function() {
                    suiteio.notify.alert({
                        msg: 'Your password has been updated',
                        type: 'success',
                        delay: -1
                    });
                },
                error: function() {
                    self.formErrorHandler.apply(self, arguments);
                }
            }).always(function() {
                $updatePasswordBtn.dynamicButton('revert');
            });
        },

        setPrivacy: function(e) {
            var currentPriv = this.settingsData.privacy
            var $target = $(e.currentTarget);
            var setting = $target.data('setting');
            var attrs = {}
            attrs.privacy = $target.data('setting');

            this.$('.privSetting .btn-radio').not($target).removeClass('checked');
            $target.addClass('checked');
            this.saveUserAttrs(attrs);
        },

        setEmailPreferences: function(e) {
            var currentPrefs = this.settingsData.emailSettings
            var $target = $(e.currentTarget);
            var settingKey = $target.data('setting');
            var settingValue = $target.hasClass('checked');
            settingValue = !settingValue;
            var attrs = {}
            attrs.emailPrefs = {
                prop: settingKey,
                propvalue: settingValue
            }
            console.log(attrs);
            $target.toggleClass('checked');
            this.saveUserAttrs(attrs);

            // $.ajax({
            //     url: this.rootUrl,
            //     type: 'POST',
            //     data: {
            //         emailprefs: true,
            //         set: setting = setting
            //     },
            //     success: function() {
            //         $target.toggleClass('checked');
            //     }
            // });
        },

        gaCodeKeyup: function(e) {
            var string = $(e.currentTarget).text();            
            var code = e.charCode || e.keyCode || e.which;
            var valid;
            if(code === 27) {
                // this.resetSlugField();
            }
            if(code === 13) {
                e.preventDefault();
                if(this.validateGaCode(string)) {
                    this.setGACode(e);
                } else {
                    return;
                }
            }
            this.validateGaCode(string)
        },

        validateGaCode: function(string) {
            var reg = /^[a-zA-Z0-9-_]+$/;
            var $targetField = this.$('.settingUserGaCode');
            var $alertContainer = this.$('.gaAlert');
            var alertMsg = '<div class="settings-alert settingsAlert">Hint: your code should only contain alphanumeric characters.</div>';
            var valid = false;
            if(!string.length) {
                valid = true;
                $targetField.removeClass('invalid');
                $alertContainer.html('').velocity('stop', true).velocity('transition.fadeOut', 250);                
            } else if (reg.test(string)) {
                valid = true;
                $targetField.removeClass('invalid');
                $alertContainer.html('').velocity('stop', true).velocity('transition.fadeOut', 250);
            } else {
                console.log('invalid');
                $targetField.addClass('invalid');
                $alertContainer.html(alertMsg).velocity('stop', true).velocity('transition.fadeIn', 250);
                valid = false;
            }
            return valid;
        },

        toggleEmailPrivacy: function(e) {
            console.log('here we go');
            var $emailRadio = this.$('.toggleEmailRadio .btn-radio');
            var currentStatus = this.settingsData.showEmail || false;
            console.log('showEmail is ' + currentStatus + ' at the start');
            var attrs = {}
            if(currentStatus) {
                this.settingsData.showEmail = attrs.showEmail = false;
            } else {
                this.settingsData.showEmail = attrs.showEmail = true;
            }
            this.saveUserAttrs(attrs);
            $emailRadio.toggleClass('checked');
        },

        setGACode: function(e) {
            e.preventDefault();
            var currentGa = this.settingsData.gaCode || suiteio.loggedInUser.get('gaCode') || '';
            var $formField = this.$('.settingUserGaCode');
            var attrs = {}
            attrs.gaCode = $formField.text(); 
            console.log('we have a code: ' + attrs.gaCode);
            var self = this;

            var doChangeGaCode = function() {
                self.saveUserAttrs(attrs);
            };

            if(!this.validateGaCode(attrs.gaCode) || attrs.gaCode == currentGa) {
                return;
            }

            console.log('length ' + attrs.gaCode.length);
            if(!attrs.gaCode.length) {
                if(!currentGa) {
                    return;
                }
                var actionDecision = {};
                actionDecision.title = 'Clear your Google Analytics code?';
                actionDecision.mainContent = '<p>You are about to save <i>nothing</i> to your Google Analytics code. It\'s entirely optional, and this isn\'t exactly dangerous, but we wanted to let you know.</p>';
                actionDecision.act1 = {
                    action: 'doChangeGaCode',
                    text: 'Clear it!'
                };
                actionDecision.act2 = {
                    action: 'godNo',
                    text: 'Cancel'
                };
                this.listenTo(suiteio.vent, 'doChangeGaCode', function() {
                    // attrs.gaCode="zilch";
                    doChangeGaCode();
                });                
                suiteio.genericActionModal(actionDecision);
            } else {
                doChangeGaCode();
            }
        },

        resetSlugField: function() {
            console.log('resetSlugField');
            var slug = this.settingsData.mySlug;
            console.log('resetting the slug to ' + slug);
            $('#settings_slug').val(slug);
        },


        slugKeyHandler: function(e) {
            var $slugField = this.$('.settingUserSlug');
            var slug = $slugField.text();            
            var code = e.charCode || e.keyCode || e.which;
            if(code === 27) {
                this.resetSlugField();
            }
            if(code === 13) {
                e.preventDefault();
                if(this.validateSlug(slug)) {
                    this.changeMySlug(e);
                } else {
                    return;
                }
            }
            this.validateSlug(slug)
        },

        validateSlug: function(slug) {
            var reg = /^[a-zA-Z0-9-_]+$/;
            var $slugField = this.$('.settingUserSlug');
            var $alertContainer = this.$('.slugAlert');
            var slug = $slugField.text();
            var slugAlert = '<div class="settings-alert settingsAlert">Your slug can only contain alphanumeric characters.</div>';
            var valid;

            if (reg.test(slug)) {
                valid = true;
                $slugField.removeClass('invalid');
                $alertContainer.html('').velocity('stop', true).velocity('transition.fadeOut', 250);
            } else {
                console.log('invalid');
                $slugField.addClass('invalid');
                $alertContainer.html(slugAlert).velocity('stop', true).velocity('transition.fadeIn', 250);
                valid = false;
            }
            return valid;
        },

        changeMySlug: function() {
            var $slugField = this.$('.settingUserSlug');
            var $alertContainer = this.$('.slugAlert');
            var newSlug = $slugField.text().trim()
            var currentSlug = this.settingsData.mySlug || suiteio.loggedInUser.get('slug') || '';
            var url = this.rootUrl;
            var self = this;
            var attrs = {};
            
            if(!this.validateSlug(newSlug) || newSlug == currentSlug) {
                return;
            }

            var actionDecision = {};
            actionDecision.title = 'Change your slug?';
            actionDecision.mainContent = '<p>Careful there, ' + suiteio.loggedInUser.get('firstName') + '. Any existing links to your profile or posts may stop working once your slug has changed.</p>';
            actionDecision.act1 = {
                action: 'doChangeSlug',
                text: 'Let\'s do it'
            };

            actionDecision.act2 = {
                action: 'godNo',
                text: 'Cancel'
            };

            suiteio.genericActionModal(actionDecision);
            this.listenTo(suiteio.vent, 'doChangeSlug', function() {
                attrs.newSlug = newSlug;
                attrs.slug = newSlug;

                $.ajax({
                    url: url,
                    dataType: 'json',
                    type: 'POST',
                    data: {
                        changeslug: true,
                        slug: newSlug
                    },
                    success: function(response) {
                        if(response.error) {
                            var slugAlert = '<div class="settings-alert settingsAlert">' + response.error + '</div>';
                            $slugField.addClass('invalid');
                            $alertContainer.html(slugAlert).velocity('stop', true).velocity('transition.fadeIn', 250);
                        } else {
                            suiteio.notify.alert({
                                msg: 'Saved!',
                                type: 'success',
                                delay: 1500
                            });
                            suiteio.loggedInUser.set('slug', newSlug);                        
                        }
                    },
                    error: function() {
                        var slugAlert = '<div class="settings-alert settingsAlert">There was a problem changing your slug. Please try again.</div>';
                        $slugField.addClass('invalid');
                        $alertContainer.html(slugAlert).velocity('stop', true).velocity('transition.fadeIn', 250);
                    }
                });

            });            
            this.listenTo(suiteio.vent, 'godNo', function() {
                $slugField.html(currentSlug);
            });  
        },
        
        submitEmailSettingsChange: function(e) {
            e.preventDefault();
            var $form = $(e.currentTarget),
                postData = {},
                self = this,
                $updateEmailSettingsButton = this.$('.updateEmailSettingsButton').dynamicButton({immediateEnable:true});


            $.each($form.find('input[type=checkbox]'), function(index, el) {
                var $el = $(el);
                postData[$el.prop('name')] = ($el.prop('checked'))? '1' : '';
            });
            return $.ajax({
                url: $form.attr('action'),
                dataType: 'json',
                type: 'POST',
                data: postData,
                success: function() {
                    suiteio.notify.alert({
                        msg: $form.find('.emailSettingsUpdateSuccess').val(),
                        type: 'success',
                        delay: -1
                    });
                },
                error: function() {
                    self.formErrorHandler.apply(self, arguments);
                }
            }).always(function() {
                $updateEmailSettingsButton.dynamicButton('revert');
            });
        },



        setupProfileImageUpload: function() {
            var self = this;
            self.uploadingMainImage = false;
            console.log('setupprofileimageupload');

            if(this.settingsImgDropzone) {
                this.settingsImgDropzone.destroy();
            }
            this.settingsImgDropzone = new Dropzone('.uploadProfileImage', { url: "/u/api/profile_img_upload", paramName: "image" });

            this.settingsImgDropzone.on("sending", function(file, xhr, formData) {
                formData.append("csrfmiddlewaretoken", suiteio.csrf);
            });

            this.settingsImgDropzone.on("success", function(data) {
                var response = JSON.parse(data.xhr.response);
                var attrs = {}
                $('.tempImageUpload').empty();
                $('.uploadProfileImage').html('');
                attrs.profileImage = response.pk
                self.saveUserAttrs(attrs);
                $('.isMe .navProfileImg').css('background-image', 'url("'+response.image_url+'")');
                $('.innerDrMe').attr('src', response.image_url).css('background-image', 'url("'+response.image_url+'")');
                self.$('.profileSettingsImage').css('background-image', 'url("'+response.image_url+'")');
            });

        },

        uploadImage: function(e) {
            console.log('trying to upload an image');
            this.setupProfileImageUpload();
            e.preventDefault();
            $('.uploadProfileImage').click();
        },

        profileFieldKeyup: function(e) {
            var self = this;
            var code = e.charCode || e.keyCode || e.which;

            if(code === 27) {
                // this.resetSlugField();
            }
            if(code === 13) {
                e.preventDefault();
                if(this.validateProfileField(e)) {
                    self.saveProfileEdit();
                } else {
                    return;
                }
            }
            self.validateProfileField(e);
        },

        validateProfileField: function(e) {
            var self = this;
            var $target = $(e.currentTarget);
            var string = $(e.currentTarget).text();            
            var field = $target.data('field');
            var valid = false;

            var validate = function() {
                var alphaNumericReg = /^[a-zA-Z0-9-_]+$/;
                switch(field) {
                    case 'byline':
                    if(!string.length) {
                        valid = true;
                        $targetField.removeClass('invalid');
                        $alertContainer.html('').velocity('stop', true).velocity('transition.fadeOut', 250);                
                    } else if (string.length > 140) {
                        console.log('invalid');
                        $targetField.addClass('invalid');
                        $alertContainer.html(alertMsg).velocity('stop', true).velocity('transition.fadeIn', 250);
                        valid = false;                        
                    }

                    // (reg.test(string)) {

                        
                    break;
                    case 'fullName':
                        self.validateName(string)
                    break;                    
                    case 'location':
                        self.validateLocation(string)
                    break;        
                    case 'website':
                        self.validateWebsite(string)
                    break;                                
                }
            };

            var reg = /^[a-zA-Z0-9-_]+$/;
            var $targetField = this.$('.settingUserGaCode');
            var $alertContainer = this.$('.gaAlert');
            var alertMsg = '<div class="settings-alert settingsAlert">Hint: your code should only contain alphanumeric characters.</div>';
            var valid = false;
            if(!string.length) {
                valid = true;
                $targetField.removeClass('invalid');
                $alertContainer.html('').velocity('stop', true).velocity('transition.fadeOut', 250);                
            } else if (reg.test(string)) {
                valid = true;
                $targetField.removeClass('invalid');
                $alertContainer.html('').velocity('stop', true).velocity('transition.fadeOut', 250);
            } else {
                console.log('invalid');
                $targetField.addClass('invalid');
                $alertContainer.html(alertMsg).velocity('stop', true).velocity('transition.fadeIn', 250);
                valid = false;
            }
            return valid;
                },

        saveProfileEdit: function() {
            var self = this;
            var nameArr, firstName, lastName, attrs = {};

            attrs.fullName = this.$('.settingUserName').text().trim() || '';
            attrs.byLine = this.$('.settingUserByline').text().trim();
            attrs.location = this.$('.settingUserLocation').text().trim();
            attrs.personalUrl = this.$('.settingUserWebsite').text().trim();

            try {
                nameArr = attrs.fullName.split(' ');
                firstName = nameArr[0];
                attrs.firstName = firstName;
                lastName = nameArr.splice(1, nameArr.length).join(' ');
                attrs.lastName = lastName;
            } catch(e) {
                attrs.firstName = attrs.fullName;
                attrs.lastName = '';
            }
            self.saveUserAttrs(attrs, true);
        },

        unlinkTwitter: function(e) {
            e.preventDefault();
            var url = $(e.currentTarget).attr('href');
            suiteio.notify.prompt({
                msg: 'Are you sure you want to unlink your Twitter account?',
                yes: 'Yes',
                no: 'No'
            }).done(function(decision) {
                if (decision) {
                    $.ajax({
                        url: url,
                        type: 'POST',
                        success: function() {
                            window.location.reload();
                        }
                    });
                }
            });
        },

        downloadMyStories: function() {
            var self = this;
            var userid = suiteio.loggedInUser.id;
             $.ajax({
                url: '/u/api/story_export/' + userid,
                type: 'POST',
                data: {},
                success: function() {
                    console.log('done');
                }
            });
        },

        getDrawerWidth: function() {    
            if(suiteio.getWindowSize().width < 480) {
                return 340; } else { return 480; }
        },

        getProfileUrl: function() {
            //getter, to prevent _profileUrl being accidentally reassigned
            return this._profileUrl;
        },
        getCoverImageUrl: function() {
            //getter, to prevent _profileUrl being accidentally reassigned
            return this._coverImageUrl;
        },
        getCoverImageUpdateUrl: function(id) {
            //getter, to prevent _profileUrl being accidentally reassigned
            return this._coverImageUpdateUrl.replace(/1234/, id);
        },
        getDeleteCoverImageUrl: function(id) {
            //getter, to prevent _profileUrl being accidentally reassigned
            return this._coverImageDeleteUrl.replace(/1234/, id);
        },
        getEmailUrl: function() {
            //getter, to prevent _emailUrl being accidentally reassigned
            return this._emailUrl;
        },
        getPwdUrl: function() {
            //getter, to prevent _pwdUrl being accidentally reassigned
            return this._pwdUrl;
        },
        getProfileImageUrl: function() {
            //getter, to prevent _profileImageUrl being accidentally reassigned
            return this._profileImageUrl;
        },

        formErrorHandler: ajaxFormErrorHandlerMixin,

        destroy: function() {
            this.destroySettingsEditors();
            this.settingsImgDropzone && this.settingsImgDropzone.destroy();
            Backbone.View.prototype.destroy.apply(this, arguments);
        }
    });
    return UserSettingsView;
});