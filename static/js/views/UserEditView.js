define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'views/UserView',
    'views/SuiteEditView', //borrowing it's editfieldfocus methods
    'lib/underwood'
],
function(
    $,
    Backbone,
    _,
    suiteio,
    UserView,
    SuiteEditView,
    Underwood
) {
    'use strict';
    var UserEditView = UserView.extend({
        events: function() {
            return _.extend({
                'show .userContentNav a[data-toggle="tab"]': 'tabChange',
                'focus .byLine': 'editFieldFocus'
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            this.model = options.model;
            this.viewname = 'usereditview';
            this.navEditContext = {
                save: {
                    primary: true
                },
                editing: true
            };
            this.hideShowEls = [
                '.tabContent',
                '.followLinks',
                '.profileLinks',
                '.actionGroup',
                '.userContentNav',
                '.bioCta',
                '.suitesList',
                '.storiesList',
                '.followersList',
                '.followingList',
                '.startEdit',
                '.favsList',
                '.storyExport',
                '.profileLinks',
                '.homeState',
                '.paginatedHomeStories',
                '.showBioInline',
                '.editStart',
                '.suiteRollup'
            ];
            this.showHideEls = [
                '.editNav',
                '.userSlugWrapper', 
                '.profileMore', 
                '.userEditControls',
                '.openSettings',
                '.longBio'
                ];
            if(!options.bootstrapped) {//SPA, expect model to sync
                this.listenToOnce(this.model, 'sync', function() {
                    this.render();
                });
            } else {//model is good to go
                var $el = $('.pageContainer#user-detail-'+this.model.id);
                if($el.length) {
                    this.setElement($el);
                    this.startEdit();
                } else {
                    this.needForceRender = true;
                }
            }
        },

        editFieldFocus: SuiteEditView.prototype.editFieldFocus,

        startEdit: function() {
            $('body').addClass('editor-active');
            this.$('.longBio').addClass('active');
            this.$('.editNav').addClass('active');
            this.editing = true;

            if(this.$('.byLine').text() === '') {
                this.$('.byLine').text(this.$('.byLine').data('placeholder'));
            }
            if(this.hideShowEls.length) {
                this.$(this.hideShowEls.join(', ')).hide();
            }
            if(this.showHideEls.length) {
                this.$(this.showHideEls.join(', ')).show();
            }
            this.$('.profileImageContainer').append('<div class="profile-image-container-overlay profileImageOverlay" data-actionbind data-action="uploadImage">Tap to add a profile image</div>');
            this.editors = {};
            this.editors.nameEditor = new Underwood(this.$('.fullName'), {
                toolbar: false,
                disableReturn: true
            });
            this.editors.byLine = new Underwood(this.$('.byLine'), {
                toolbar: false,
                disableReturn: true,
                characterLimit: 140
            });
            this.bioEditor = new Underwood(this.$('.fullBio'), {
                toolbar: {
                    buttons: [
                        'anchor',
                        'bold',
                        'italic',
                        'strikethrough', 
                        'unorderedlist',
                        'justifyLeft',
                        'justifyCenter',
                        'justifyRight'            
                    ],
                    firstHeader: 'h2',
                    secondHeader: 'h2'
                }
            });

            if(this.$('.fullBio') == '') {
                this.hasbio = false;
            }
            this.setupImageUpload();
        },

        render: function() {
            UserView.prototype.render.apply(this, arguments); //call super
            this.startEdit();
        },

        endEdit: function(isCancel) {
            this.deactivateEditors();
            $('body').removeClass('editor-active');
            this.$('.longBio').removeClass('active');
            this.$('.editNav').removeClass('active');
            self.editing = false;
            if(isCancel) {
                this.$('.fullName').text(this.model.get('fullName'));
                this.$('.byLine').text(this.model.get('byLine'));
                this.$('.fullBio').html(this.model.get('fullBio'));
                this.$('.profileImageContainer').find('img').attr({
                    src: this.model.get('mainImageUrl'),
                    alt: this.model.get('fullName'),
                    title: this.model.get('fullName')
                }).css({
                    'background-image': 'url("' + this.model.get('mainImageUrl') + '")'
                });
            }
            if(this.hideShowEls.length) {
                this.$(this.hideShowEls.join(', ')).show();
            }
            if(this.showHideEls.length) {
                this.$(this.showHideEls.join(', ')).hide();
            }
            this.$('.profileImageOverlay').remove();
            this.trigger('doneEditMode', this.model);
        },

        saveEdit: function() {
            var name = this.$('.fullName').text(),
                byLine = this.$('.byLine').text(),
                fullBio = this.$('.fullBio').html(),
                self = this,
                nameArr,
                firstName,
                lastName,
                attrs = {
                    fullName: name
                };

            attrs.location = this.$('input[name="location"]').val();
            attrs.facebookUrl = this.$('input[name="facebook"]').val();
            attrs.twitterUsername = this.$('input[name="twitterUsername"]').val();
            attrs.personalUrl = this.$('input[name="personalUrl"]').val();
            this.model.checkSetByline(byLine);
            this.model.checkSetFullBio(fullBio);
            if(this.model.get('byLine') === '') {
                this.$('.byLine').html('');
            }
            if(this.model.get('fullBio') === '') {
                this.$('.fullBio').html('');
            }
            try {
                nameArr = name.split(' ');
                firstName = nameArr[0];
                attrs.firstName = firstName;
                lastName = nameArr.splice(1, nameArr.length).join(' ');
                attrs.lastName = lastName;
            } catch(e) {
                attrs.firstName = name;
                attrs.lastName = '';
            }
            this.listenToOnce(this.model, 'invalid', function(model, error) {
                var msg = error,
                    type = 'error';
                suiteio.notify.alert({
                    type: type,
                    msg: msg
                });
            });
            this.model.save(attrs, {
                wait: true,
                success: function() {
                    self.endEdit();
                },
                error: function(model, resp) {
                    var type = 'error',
                        msg = 'There has been an error processing your profile, please try again later';
                    suiteio.notify.alert({
                        type: type,
                        msg: msg
                    });
                }
            });
        },

        deactivateEditors: function() {
            var editor;
            if(this.editors) {
                for(var key in this.editors) {
                    editor = this.editors[key];
                    editor.destroy();
                }
            }
        },

        setupImageUpload: function() {
            var self = this,
                selector = '.uploadProfileImage',
                _formData = [{ name: 'csrfmiddlewaretoken', value: suiteio.csrf }];
            this.$(selector).fileupload({
                formData: _formData,
                url: '/u/api/profile_img_upload',
                dataType: 'json',
                dropZone: this.$el,
                add: function (e, data) {
                    var _URL = window.URL || window.webkitURL,
                        file, img;
                    if ((file = data.files[0])) {
                        img = new Image();
                        img.onload = function () {
                            data.submit();
                        };
                        img.src = _URL.createObjectURL(file);
                    }
                },
                done: function (e, data) {
                    //done
                    self.model.set('profileImage', data.result.pk);
                    self.$('.profileImage').attr('src', data.result.image_url).css('background-image', 'url("'+data.result.image_url+'")');
                }
            });
        },

        uploadImage: function(e) {
            e.preventDefault();
            this.$('.uploadProfileImage').click();
        },

        destroy: function() {
            this.deactivateEditors();
            UserView.prototype.destroy.apply(this, arguments);
        }
    });
    return UserEditView;
});