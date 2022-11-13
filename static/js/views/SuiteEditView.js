define([
    'jquery',
    'backbone',
    'underscore',
    'views/SuiteView',
    'lib/underwood',
    'lib/Countable',
    'interact',
    'dropzone',
    'suiteio',
    'lib/rangy-core'
], function(
    $,
    Backbone,
    _,
    SuiteView,
    Underwood,
    Countable,
    interact,
    Dropzone,
    suiteio,
    rangy
) {
    'use strict';
    var selectElementContents = function (el) {
        var range = document.createRange();
        range.selectNodeContents(el);
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    };
    var SuiteEditView = SuiteView.extend({
        events: function() {
            return _.extend({
                    'click .suiteAuthors a': function(e) {e.preventDefault();},
                    'focus .ctrPlaceholder': 'editFieldFocus'
                }, _.result(SuiteView.prototype, 'events')
            );
        },
 
        initialize: function(options) {
            SuiteView.prototype.initialize.apply(this, arguments);
            this.viewname = 'suiteeditview';

            this.setupShowHideEls();
            this.startEdit();
            this.dirty = false;
            this.coverType = this.model.get('coverType') || 'image';            
            this.suiteBackgroundTmpl = suiteio.templateLoader.getTemplate('suite-background-edit');            
        },

        selectElement: function(selectEl) {
            var range = rangy.createRange();
            range.selectNodeContents(selectEl);
            var sel = rangy.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        },
 
        editFieldFocus: function(e) {
            var $ctarget = $(e.currentTarget),
                val = $ctarget.text(),
                placeholder = $ctarget.data('placeholder');
                var selectEl = $ctarget.get(0);
            if(val === placeholder || val === '') {
                if(val === '') {
                    $ctarget.text(placeholder);
                }
                this.selectElement(selectEl);
            }
        },

        setupShowHideEls: function() {
            this.hideShowEls = [
                '.actionButts',
                '.editTitlePage',
                '.shareActions',
                '.heroCaption',
                '.suiteAuth',
                '.memberPanel',
                '.primaryTabs',
                '.suiteManageGroup'
            ];
            this.showHideEls = [
                '.colorSwitch',
                '.suiteImageControls',
                '.suiteEditNav'
            ];
        },

        setDirtyFlag: function() {
            this.dirty = true;
            // let's leave the buttons alone for now

        },

        suiteEditNavOut: function() {
            $('.suiteEditNav').velocity('stop', true).velocity({ bottom: -64 }, { duration: 250, easing: [ 0.19, 1, 0.22, 1 ] });            
            $('.navbar').velocity('stop', true).velocity({ top: 0 }, { duration: 250, easing: [ 0.19, 1, 0.22, 1 ] });           
        },

        suiteEditNavIn: function() {
            $('.suiteEditNav').velocity('stop', true).velocity({ bottom: 0 }, { duration: 250, easing: [ 0.19, 1, 0.22, 1 ] });            
            $('.navbar').velocity('stop', true).velocity({ top: -64 }, { duration: 250, easing: [ 0.19, 1, 0.22, 1 ] });
        },

        startEdit: function() {
            var self = this;
            this.suiteEditNavIn();
            this.closeSuiteManageOptions();

            var $titleEl = this.$('.suiteName');
            var $descriptionEl = this.$('.suiteDescription');

            this.editing = true;
            this.hideCaptionPopup();
            $('body').addClass('cover-editor-active');
            this.$('.editFuncs').addClass('editing');
            if(this.hideShowEls.length) {
                this.$(this.hideShowEls.join(', ')).hide();
            }
            if(this.showHideEls.length) {
                this.$(this.showHideEls.join(', ')).show();
            }

            if(!this.model.get('activeHero')) {
                this.$('.suiteImageControls').show();
            }
            this.nameEditor = new Underwood(this.$('.suiteName'), {
                toolbar: false,
                disableReturn: true,
                spellcheck: false,
                placeholder: {
                    hideOnClick: false,
                    text: 'Give your Suite a name'
                },
            });
            this.descriptEditor = new Underwood(this.$('.suiteDescription'), {
                toolbar: false,
                disableReturn: true,
                spellcheck: false,
                placeholder: {
                    hideOnClick: false,
                    text: 'Add a brief description'
                },                    
            });
            if(this.$('.suiteDescription').text() === '') {
                this.$('.suiteDescription').text(this.$('.suiteDescription').data('placeholder'));
            }

            this.listenTo(this.model, 'invalid', function(model, error) {
                this.$('[data-action=saveSuite]').dynamicButton('revert');
                suiteio.notify.alert({
                    type: 'error',
                    msg: error
                });
            });


            // this.listenTo(this.imageManagerView, 'uploadImageDone', function(data) {
            //     var imageUrl = data.image_url,
            //         // resourceUri = data.resource_uri,
            //         pk = data.pk;
            //     this.$el.removeClass('no-image');
            //     this.$('.heroImg').data('id', pk).css({
            //         'background-image': 'url("' + imageUrl + '");'
            //     });
            // });

            this.$('.descContainer').append('<span class="inline-wordcount descCount inlineCounter"></span>');
            this.$('.titleContainer').append('<span class="inline-wordcount titleCount inlineCounter"></span>');

            this.descriptionCounter = Countable.live($descriptionEl.get(0), function(counter) {
                self.updateWordCount(counter.all, 'description');
                if(!counter.characters) {
                    var placeholder = $descriptionEl.data('placeholder');
                    $descriptionEl.text(placeholder);
                    self.selectElement($descriptionEl.get(0));
                }                
            });
            this.nameCountable = Countable.live($titleEl.get(0), function(counter) {
                self.updateWordCount(counter.all, 'title');
                if(!counter.characters) {
                    var placeholder = $titleEl.data('placeholder');
                    $titleEl.text(placeholder);
                    self.selectElement($titleEl.get(0));
                }
            });

            $('body').off('.suitesavekeypress').on('keydown.suitesavekeypress', function(e) {
                var code = e.charCode || e.keyCode || e.which;
                if((code === 83 && (e.ctrlKey||e.metaKey)) || code === 19) {
                    e.preventDefault();
                    self.saveSuite();
                    return false;
                }
            });
        },

        toggleBackgroundEdit: function() {
            var self = this;
            var color = this.model.get('color');
            var coverTypeImage, coverTypeColor = false;
            if(this.coverType=='image') {
                coverTypeImage = true;
            } else {
                coverTypeColor = true;
            }
            
            var $backgroundEditContainer = this.$('.backgroundEditContainer');


            if(!this.$backgroundEditPanel) {
                this.suiteBackgroundTmpl.done(function(tmpl) {
                    self.$backgroundEditPanel = $(tmpl({
                        color: color,
                        coverTypeImage: coverTypeImage,
                        coverTypeColor: coverTypeColor
                    }));

                    $backgroundEditContainer.html(self.$backgroundEditPanel);
                    self.$backgroundEditPanel.velocity('stop', true).velocity({ bottom: 56 }, { duration: 250, easing: [ 0.19, 1, 0.22, 1 ] });    
                    // self.$('.suiteDetails').velocity('stop', true).velocity({ paddingBottom: 4 }, { duration: 250, easing: [ 0.19, 1, 0.22, 1 ] });        

                    self.$backgroundEditPanel.on('click', '.insertUploadImage', function(e) {
                        console.log('ok!');
                        self.startUpload(e);
                    });

                    // self.$insertPanel.on('click', '.insertShowEmbed', function(e) {
                    //     console.log('show embed form');
                    //     self.showEmbedLink(e);
                    // });

                    self.$backgroundEditPanel.on('keypress', '.mediaEmbedInput', function(e) {
                        self.embedKeyup(e);
                    });  

                    self.listenToOnce(suiteio.keyWatcher, 'keydown:27', function() {
                        self.closeBackgroundEdit();
                    });

                });
            } else {
                self.closeBackgroundEdit();
            }            
        },

        rgbToHex: function(r,g,b) {
            var componentToHex = function(c) {
                // set upper/lower limits
                if(c>255) {
                    c = 255;
                } else if(c < 0) {
                    c = 0;
                }                
                var hex = c.toString(16);
                return hex.length == 1 ? "0" + hex : hex;
            }
            return "#" + componentToHex(r) + componentToHex(g) + componentToHex(b);
        },

        hexToRgb: function(hex) {
            // Expand shorthand form (e.g. "03F") to full form (e.g. "0033FF")
            var shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
            hex = hex.replace(shorthandRegex, function(m, r, g, b) {
                return r + r + g + g + b + b;
            });

            var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
            return result ? {
                r: parseInt(result[1], 16),
                g: parseInt(result[2], 16),
                b: parseInt(result[3], 16)
            } : null;
        },

        initRgbInteractions: function() {
            var self = this;
            var elementHeight = this.$('.sliderRange').height();
            var gripHeight = this.$('.rgbSlider').height();
            var rgbRange = (elementHeight - gripHeight);
            var $blueInput = this.$('.rgbInputBlue');            
            var $redInput = this.$('.rgbInputRed');
            var $greenInput = this.$('.rgbInputGreen');
            var currentHex = this.model.get('color') || '#313a3f';
            var currentRgb = this.hexToRgb(currentHex);
            var $detailHero = this.$('.detailHero');

            $detailHero.addClass('no-image');
            var cRed=currentRgb.r, cGreen=currentRgb.g, cBlue=currentRgb.b;
            var sliderRatio, colVal;

            $redInput.val(cRed);
            $greenInput.val(cGreen);
            $blueInput.val(cBlue);

            var rInitPos = Math.round(((255-cRed)/255) * rgbRange);
            var gInitPos = Math.round(((255-cGreen)/255) * rgbRange);
            var bInitPos = Math.round(((255-cBlue)/255) * rgbRange);

            this.$('.redSlider').get(0).setAttribute('data-y',rInitPos);
            this.$('.greenSlider').get(0).setAttribute('data-y',gInitPos);
            this.$('.blueSlider').get(0).setAttribute('data-y',bInitPos);

            this.$('.redSlider').velocity('stop', true).velocity({ translateY: rInitPos }, { duration: 500, easing: [ 0.19, 1, 0.22, 1 ] });            
            this.$('.greenSlider').velocity('stop', true).velocity({ translateY: gInitPos }, { duration: 500, easing: [ 0.19, 1, 0.22, 1 ] });            
            this.$('.blueSlider').velocity('stop', true).velocity({ translateY: bInitPos }, { duration: 500, easing: [ 0.19, 1, 0.22, 1 ] });            

            // target elements with the "draggable" class
            interact('.draggable')
              .draggable({
                // enable inertial throwing
                // inertia: true,
                // axis: 'y',
                // keep the element within the area of it's parent
                restrict: {
                  restriction: 'parent',
                  endOnly: false,
                  elementRect: { top: 0, left: 0, bottom: 1, right: 1 }
                },
                // enable autoScroll
                autoScroll: false,

                // call this function on every dragmove event
                onmove: dragMoveListener,
                // call this function on every dragend event
                onend: function (event) {
                  var textEl = event.target.querySelector('p');

                  textEl && (textEl.textContent =
                    'moved a distance of '
                    + (Math.sqrt(event.dx * event.dx +
                                 event.dy * event.dy)|0) + 'px');
                }
              });

              function dragMoveListener (event) {
                var target = event.target,
                    // keep the dragged position in the data-x/data-y attributes
                    x = (parseFloat(target.getAttribute('data-x')) || 0) + event.dx,
                    y = (parseFloat(target.getAttribute('data-y')) || 0) + event.dy;
                    sliderRatio = (y/rgbRange);
                    colVal = (255 - Math.round((sliderRatio * 255)));
                    var colComponent = $(target).data('color');
                    
                    if(colVal>255) {
                        colVal = 255;
                    } else if(colVal < 0) {
                        colVal = 0;
                    }
                    switch(colComponent) {
                        case 'blue':
                            cBlue = colVal;
                            $blueInput.val(cBlue);
                        break;                        
                        case 'red':
                            cRed = colVal;
                            $redInput.val(cRed);
                        break;
                        case 'green':
                            cGreen = colVal;
                            $greenInput.val(cGreen);
                        break;
                    }
                
                currentHex = self.rgbToHex(cRed,cGreen,cBlue);
                self.$('.hexColorInput').val(currentHex);
                $detailHero.css('backgroundColor', currentHex);
                self.hexColor = currentHex;
                
                var lum = 0.2126*cRed + 0.7152*cGreen + 0.0722*cBlue;
                var lum2 = Math.sqrt(0.299 * cRed^2 + 0.587 * cGreen^2 + 0.114 * cBlue^2);
                console.log(lum2);
                console.log('luminosity: ' + lum);
                if(lum>230) {
                    self.$('.ctrPlaceholder').css('color', 'rgba(0,0,0,.6)');
                } else {
                    self.$('.ctrPlaceholder').css('color', 'rgba(255,255,255,.96)');
                }

                // translate the element
                target.style.webkitTransform =
                target.style.transform =
                  'translate(' + x + 'px, ' + y + 'px)';

                // update the posiion attributes
                target.setAttribute('data-x', x);
                target.setAttribute('data-y', y);
              }

              // this is used later in the resizing and gesture demos
              window.dragMoveListener = dragMoveListener;

            document.addEventListener('dragstart', function (event) {
                // use interact.js' matchesSelector polyfil to
                // check for match with your draggable target
                if (interact.matchesSelector(event.target, '.draggable')) {
                    // prevent and stop the event if it's on a draggable target
                    event.preventDefault();
                    event.stopPropagation();
                }
            }); 
        },

        toggleBackgroundType: function(e) {
            var $selector = $(e.currentTarget);
            var activeType = $selector.data('type');

            this.$('.bkTypeTab').not($selector).removeClass('active');
            $selector.addClass('active');
            if(activeType=='image') {
                this.coverType = 'image';
                this.$('.colorMixer').removeClass('active');
                this.$('.imageSelector').addClass('active');
            } else if(activeType=='color') {
                this.coverType = 'color';
                this.$('.colorMixer').addClass('active');
                this.$('.imageSelector').removeClass('active');                
                this.initRgbInteractions();
            }
        },

        closeBackgroundEdit: function() {
            this.$backgroundEditPanel.velocity('stop', true).velocity('reverse');       
            // this.$('.suiteDetails').velocity('stop', true).velocity('reverse');        
            this.$backgroundEditPanel.off('.insertUploadImage').off('.insertShowEmbed').off('.mediaEmbedInput');
            this.$backgroundEditPanel.remove();
            this.$backgroundEditPanel = null;
        },

        showSuiteColorMixer: function() {
            console.log('start up color mixer');
        },

        updateWordCount: function(chars, field) {
            var limit, container, element;
            switch(field) {
                case 'description':
                    limit = 140;
                    container = this.$('.descCount');
                    element = this.$('.suiteDescription');                
                break;
                case 'title':
                    limit = 80;
                    container = this.$('.titleCount');
                    element = this.$('.suiteName');
                break;
            }
            
            var isWhitespace = function(string) {
                return /^\s+$/.test(string);
            }

            if(chars>limit) {
                console.log('reached limit of ' + limit);
                element.text(element.text().substring(0,limit));
                // element.focus();
                this.setEndOfElement(element.get(0));                
                return;
            }
            if(!chars || isWhitespace(element.text())) {
                chars = '';
            }
            container.html(chars);            
        },

        setEndOfElement: function(element)
        {
            var range,selection;
            if(document.createRange)//Firefox, Chrome, Opera, Safari, IE 9+
            {
                range = document.createRange();//Create a range (a range is a like the selection but invisible)
                range.selectNodeContents(element);//Select the entire contents of the element with the range
                range.collapse(false);//collapse the range to the end point. false means collapse to end rather than the start
                selection = window.getSelection();//get the selection object (allows you to change selection)
                selection.removeAllRanges();//remove any selections already made
                selection.addRange(range);//make the range you have just created the visible selection
            }
            else if(document.selection)//IE 8 and lower
            { 
                range = document.body.createTextRange();//Create a range (a range is a like the selection but invisible)
                range.moveToElementText(element);//Select the entire contents of the element with the range
                range.collapse(false);//collapse the range to the end point. false means collapse to end rather than the start
                range.select();//Select the range (make it the visible selection
            }
        },

        startUpload: function(e) {
            this.setupImageUpload();
            this.$('.suiteImgDropZone').click();
        },

        setupImageUpload: function() {
            var self = this;
            console.log('should be setting up the image upload...');
            this.imgDropzone && this.imgDropzone.destroy();
            this.imgDropzone = new Dropzone(".suiteImgDropZone", { url: "/a/api/image_upload", paramName: "image", maxFilesize: 16 });

            this.imgDropzone.on("sending", function(file, xhr, formData) {
                console.log(formData);
                self.activeStoryUpload = true;
                // send the csrf token with the upload
                formData.append("csrfmiddlewaretoken", suiteio.csrf);
                if(!self.uploadingMainImage) {  
                    var $loader = $('<figure class="plain image-uploading-shell imageUploadingShell" contenteditable="false"></figure>');
                    // Inject the figure uploading shell
                    if(self.$selectedHotspot && self.$selectedHotspot.length) {
                        self.$selectedHotspot.replaceWith($loader);
                    } else if (self.$clickedImageTargetEl && self.$clickedImageTargetEl.length) {
                        self.$clickedImageTargetEl.before($loader);
                    }
                }
            });

            this.imgDropzone.on("success", function(data) {
                var response = JSON.parse(data.xhr.response);
                if(response.error) {
                    console.log('we have detected an error: ' + response.error);
                    $('.storyMediaDropZone').html('');
                    self.insertErrorAlert(response.error);
                    return;
                }
                self.stagedMedia = response
                self.placeMedia();
                $('.storyMediaDropZone').html('');
            });
        },

        embedKeyup: function(e) {
            var code = e.charCode || e.keyCode || e.which;
            if(code === 13) {
                e.preventDefault();
                this.fetchImageFromInput();
            }
        },

        fetchImageFromInput: function(e) {
            var self = this;
            var $embedInput = $('.mediaEmbedInput');
            var embedString = $embedInput.val();
            var url = '/s/api/input_upload';
            $embedInput.before(self.loader);
            console.log('embed string: ' + embedString);

            $.ajax({
                url: url,
                type: 'POST',
                data: {
                    embedstring: embedString,
                    coverimage: self.uploadingMainImage
                },
                success: function(response) {
                    self.stagedMedia = response;
                    self.placeImage();

                },
                error: function(response) {
                    console.log('an error has occurred'); console.log(response);
                },
            }).always(function() {
                console.log('remove loader!');
                self.$('.loaderBox').remove();
            });

        },




       goBack: function() {
            if(window.history.length) {
                window.history.back();
            } else {
                window.location.href = "/";
            }
        },

        toggleEditAction: function() {
            var self = this;
            if(this.processingSave) {
                return;
            }
            if(this.viewname === 'suiteeditview') {
                if(this.isDirty()) {
                    suiteio.notify.prompt({
                        msg: 'Save your changes?'
                    }).done(function(decision) {
                        if(decision) {
                            self.saveSuite({}, true, true);
                        } else {
                            //dirty and we're not saving, revert
                            self.endEdit({revert: true});
                        }
                    });
                } else {
                    //clean, no need to revert
                    this.endEdit({revert: false});
                }
            } else {
                this.goBack();
            }
        },
 
        saveSuite: function(e, isRetry) {
            var $btn = this.$('.saveSuite');
            var self = this,
                suiteName = this.$('.suiteName').text(),
                suiteDescription = this.$('.suiteDescription').text(),
                saveImagePromise;
            var coverType = this.coverType;
            var color = this.hexColor;
            if(!isRetry) {
                $btn.dynamicButton({immediateEnable: true});
            }
            saveImagePromise = this.imageManagerView.saveImageAttributes();
            saveImagePromise.always(function() {
                self.model.checkSetDescription(suiteDescription);
                var saveSuitePromise = self.model.save({
                    coverType: coverType,
                    color: color,
                    name: suiteName //description and about are set in the checkSetDescription and checkSetAbout methods
                }, {
                    wait: true,
                    success: function(model) {
                        self.endEdit({model: model});
                    },
                    error: function(model, resp) {
                        var type = 'error',
                            msg = 'There has been an error processing your Suite, please try again later';
                        suiteio.notify.alert({
                            type: type,
                            msg: msg
                        });
                    }
                });
                if(saveSuitePromise && saveSuitePromise.always) {
                    saveSuitePromise.always(function() {
                        $btn.dynamicButton('revert');
                    });
                }
            });
        },

        isDirty: function() {
            if(this.modelDeleted === true) {
                return false;
            }
            return this.dirty;
        },

        removeDirtyFlag: function() {
            this.dirty = false;
            this.$('.saveStay').removeClass('btn-blue changed');
            this.$('.didSave').show();
        },
 
        endEdit: function(options) {
            var self = this;
            this.suiteEditNavOut();
            var wait = setTimeout(function() { 

                self.editing = false;
                $('body').removeClass('cover-editor-active');
                this.$('.editFuncs').removeClass('editing');

                if(self.hideShowEls.length) {
                    self.$(self.hideShowEls.join(', ')).show();
                }
                if(self.showHideEls.length) {
                    self.$(self.showHideEls.join(', ')).hide();
                }
                self.$('.inlineCounter').remove();
                self.nameEditor.destroy();
                self.descriptEditor.destroy();
                self.trigger('doneEditMode', self.model);

            }, 100);
        },
 
        destroy: function() {
            this.nameCountable.die(this.$('.suiteName').get(0));
            this.descriptionCounter.die(this.$('.suiteDescription').get(0));
            this.imageManagerView && this.imageManagerView.destroy();
            SuiteView.prototype.destroy.apply(this, arguments);
        }
    });
    return SuiteEditView;
});