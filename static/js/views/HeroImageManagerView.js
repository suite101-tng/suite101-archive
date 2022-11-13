define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'dropzone',
    'helpers/jquery.autoExpandTextarea'
], function(
    $,
    Backbone,
    _,
    suiteio,
    Dropzone
) {
    'use strict';
    var convertImgToBase64 = suiteio.convertImgToBase64;
    var HeroImageManagerView = Backbone.View.extend({
        
        events: function() {
            return _.extend({
                    'blur .heroCaptionEdit .inputs': 'captionInputBlur'
                }, _.result(Backbone.View.prototype, 'events')
            );
        },
        
        initialize: function(options) {
            this.options = options;
            if(options.el) {
                this.setElement(options.el);
            }
            this.model = options.model;
            this.setupImageUpload();
            this.$('.heroCaptionEdit textarea').autoExpandTextarea();
            this.suiteHeroTmplPromise = suiteio.templateLoader.getTemplate('suite-hero');
        },
        
        saveImageAttributes: function() {
            var returnPromise = $.Deferred();
            if(this.model.heroImageModel && this.model.heroImageModel.hasChanged()) {
                this.model.heroImageModel.save({}, {
                    success: function() {
                        returnPromise.resolve.apply(null, arguments);
                    },
                    error: function() {
                        returnPromise.reject.apply(null, arguments);  
                    }
                });
            } else {
                returnPromise.resolve();
            }
            return returnPromise;
        },
        
        deleteImage: function(e) {
            try { e.preventDefault(); } catch(err) {}
            this.model.heroImageModel.removeHeroImage();
            this.trigger('deleteHeroImage');
        },
                
        captionInputBlur: function(e) {
            var $ctarget = $(e.currentTarget),
                field = $ctarget.attr('name'),
                value = $ctarget.val();
            if(this.model.heroImageModel.get(field) !== value) {
                this.model.heroImageModel.set(field, value);
                console.log('captionInputBlur');
            }
        },
        
        clearCaptionFields: function() {
            this.$('.heroCaptionEdit .inputs').val('');
        },
        
        changeImage: function(e) {
            try { e.preventDefault(); } catch(err) {}
            this.$('.suiteImgDropZone').click();
        },
        
        setupImageUpload: function() {
            var self = this;
            self.imgDropzone = new Dropzone(".mydropzone", { url: "/s/image/upload", paramName: "image", maxFilesize: 16 });

            self.imgDropzone.on("sending", function(file, xhr, formData) {
                // send the csrf token with the upload
                formData.append("csrfmiddlewaretoken", suiteio.csrf);
              
                if(!self.uploadingMainImage) {
                    var $loader = $('<figure class="plain image-uploading-shell imageUploadingShell" contenteditable="false"></figure>');
                    // Inject the figure uploading shell
                    if(self.$selectedHotspot && self.$selectedHotspot.length) {
                        self.$selectedHotspot.replaceWith($loader);
                    } else if (self.$clickedImageTargetEl && self.$clickedImageTargetEl.length) {
                        console.log('trying to attach the loader to the dom');
                        self.$clickedImageTargetEl.before($loader);
                    }
                }
            });

            self.imgDropzone.on("thumbnail", function(file, dataUrl) {
                console.log(dataUrl);
            });

            self.imgDropzone.on("success", function(data) {
                var response = JSON.parse(data.xhr.response);
                self.placeHero(response);
                $('.tempImageUpload').empty();
                $('.suiteImgDropZone').html('');
            });
        },

        placeHero: function(result) {
            var self = this;
            var img = new Image();
            img.src = result.image_large_url;
            console.log('result');
            console.log(result);
            if(result.pk) {
                $(img).attr({'data-id': result.pk});
            }

            self.suiteHeroTmplPromise.done(function(tmpl) {
                var $wrapper = $(tmpl({
                        credit: '',
                        creditLink: '',
                        caption: '',
                        largeImageUrl: result.image_large_url,
                        origImageUrl: result.image_url,
                        id: result.pk,
                    }));
                self.$('.suiteImageContainer').html($wrapper);
            });

            self.clearCaptionFields();
            console.log(self.model);
            self.model.setHeroImage({
                type: 'suite',
                user: suiteio.loggedInUser,
                id: result.pk,
                largeImageUrl: null,
                origImageUrl: result.image_url,
                resourceUri: result.resource_uri
            });
            self.trigger('uploadImageDone', result);
        },
       
        destroy: function() {
            Backbone.View.prototype.destroy.apply(this, arguments);
        }
    });
    return HeroImageManagerView;
});