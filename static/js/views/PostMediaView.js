    define([
    'jquery',
    'underscore',
    'backbone',
    'suiteio',
    'interact',
    'dropzone',
    'autosize'
],
function(
    $,
    _,
    Backbone,
    suiteio,
    interact,
    Dropzone,
    autosize
) {
    'use strict';
    var spacerBeforeImage = '<p class="spacerBeforeImage"></p>';
    var PostMediaView = Backbone.View.extend({
        
        events: function() {
            return _.extend({
                'keyup .captionEdit': 'captionKeyup',
                'click .insertError': 'hideInsertError'
            }, _.result(Backbone.View.prototype, 'events'));
        },
        
        initialize: function(options) {
            var self = this;
            this.setElement(options.el);
            this.loader = '<div class="loader-box loaderBox blue medium"><span class="suite-logo loader-spin"></span><div class="texty">Loading</div></div>';
            
            this.insertMediaPanelTmpl = suiteio.templateLoader.getTemplate('media-insert');
            this.storyEmbedTmpl = suiteio.templateLoader.getTemplate('story-embed');
            this.storyEmbedEditTmpl = suiteio.templateLoader.getTemplate('story-embed-edit');

            this.newPost = options.newPost || false;
            this.storyElements = [];
            this.postModel = options.postModel;
            this.imagesCollection = options.images;

            this.embedsCollection =  {};
            this.activeStoryUpload = false;

            this.insertHere = null;
            this.moveables = [
                '.storyBody > p',
                '.storyBody > figure',
                '.storyBody > h2',
                '.storyBody > blockquote',
                '.storyBody > ol',
                '.storyBody > hr',
                '.storyBody > ul'
            ].join(',');

            this.imageModeActivated = false;
            this.stagedMedia = null;

            this.inProgress = false;
            this.preProcessEmbeds();
            autosize(this.$('.captionEdit'));          

            this.setupDraggables();
        },

        startInsert: function() {
            var self = this;
            var $parent, $parentEl, cursorInBody;
            var storyId = self.postModel.id || 'new';
            this.insertBefore = false;
            this.insertTarget = null;

            var getCaretPosition = function(element) {
                var ie = (typeof document.selection != "undefined" && document.selection.type != "Control") && true;
                var w3 = (typeof window.getSelection != "undefined") && true;                
                var caretOffset = 0;
                var fullLength;
                if (w3) {
                    var range = window.getSelection().getRangeAt(0);
                    var preCaretRange = range.cloneRange();
                    preCaretRange.selectNodeContents(element);
                    fullLength = preCaretRange.toString().length;
                    preCaretRange.setEnd(range.endContainer, range.endOffset);
                    caretOffset = preCaretRange.toString().length;
                } else if (ie) {
                    var textRange = document.selection.createRange();
                    var preCaretTextRange = document.body.createTextRange();
                    fullLength = preCaretTextRange.text.length;
                    preCaretTextRange.moveToElementText(element);
                    preCaretTextRange.setEndPoint("EndToEnd", textRange);
                    caretOffset = preCaretTextRange.text.length;
                }
                return [caretOffset, fullLength];
            }

            // get current cursor position
            var getSelectedNode = function() {
                var node,selection;
                if (window.getSelection) {
                  selection = getSelection();
                  node = selection.anchorNode;
                }  if (!node && document.selection) {
                    selection = document.selection;
                    var range = selection.getRangeAt ? selection.getRangeAt(0) : selection.createRange();
                    node = range.commonAncestorContainer ? range.commonAncestorContainer :
                           range.parentElement ? range.parentElement() : range.item(0);
                }
                if (node) {
                  return (node.nodeName == "#text" ? node.parentNode : node);
                } else {
                    return null;
                }
            };

            $parent = getSelectedNode();

            var storyElChildren = this.$('.storyBody').children();

            var descendantIndex = $.inArray($parent, storyElChildren);
            if(!descendantIndex) {
                this.insertTarget = $($parent);
            } else if(descendantIndex>0) {
                this.insertTarget = $($parent);
            } 

            try {
                var positionValues = getCaretPosition(this.insertTarget.get(0));
                var caret = positionValues[0] || 0;
                var fullLength = positionValues[1] || 1;
                var position = (caret / fullLength);
                if(position<.5) {
                    this.insertBefore = true;
                } 
            } catch(e) {
                console.log('pos');
            }

            if(!this.$insertPanel) {
                this.insertMediaPanelTmpl.done(function(tmpl) {
                    self.$insertPanel = $(tmpl({
                        id: storyId
                    }));
                    self.$('.editNav').append(self.$insertPanel);
                    self.$('.storyEditControls').addClass('media');
                    self.$('.insertTrigger').addClass('media');

                    self.$('.insertSelector').velocity('stop', true).velocity('transition.slideLeftBigIn', { duration: 250, easing: [ 0.19, 1, 0.22, 1 ] });            
                    self.$insertPanel.velocity('stop', true).velocity({ top: 54 }, { duration: 250, easing: [ 0.19, 1, 0.22, 1 ] });            

                    self.$insertPanel.on('click', '.insertUploadImage', function(e) {
                        self.startUpload(e);
                    });

                    self.$insertPanel.on('keypress', '.mediaEmbedInput', function(e) {
                        self.embedKeyup(e);
                    });    
                    // self.listenToOnce(suiteio.keyWatcher, 'keydown:27', function() {
                    //     self.closeMediaInsert();
                    // });

                });
            } else {
                self.closeMediaInsert();
            }
        },

        closeMediaInsert: function() {
            this.$insertPanel.velocity('stop', true).velocity('reverse');
            this.$('.insertSelector').velocity('stop', true).velocity('reverse');            
            this.$insertPanel.off('.insertUploadImage').off('.mediaEmbedInput');
            this.$insertPanel.remove();
            this.$insertPanel = null;
            this.$('.storyEditControls').removeClass('media');
            this.$('.insertTrigger').removeClass('media');
        },

        setupDraggables: function() {
            this.setupDragDrop();
        },

        setupDragDrop: function() {
            var that = this;
            self = this;
            var $currentClone;
            var moveables = this.moveables;

            document.addEventListener('dragstart', function (event) {
                // use interact.js' matchesSelector polyfil to
                // check for match with your draggable target
                if (interact.matchesSelector(event.target, '.draggable')) {
                    // prevent and stop the event if it's on a draggable target
                    event.preventDefault();
                    event.stopPropagation();
                }
            });             

            interact(moveables)
                .allowFrom('.dragHandle')
              .draggable({
                inertia: true,
                restrict: {
                  restriction: "parent"
                },
                autoScroll: true           
              })
             
            // drag from handle
            .on('dragstart', dragMoveListener)

              .on('dragmove dragend', dragMoveListener)
              .on(['resizemove', 'resizeend'], dragMoveListener)
              .on({
                gesturestart: dragMoveListener,
                gestureend: dragMoveListener
              })
                .on('dragstart', function(event) {
                    self.clone = event.target.cloneNode(true);
                    event.target.classList.add('draggable', 'moving');
                    self.$('article').addClass('dragging');
                    self.listenToOnce(suiteio.keyWatcher, 'keydown:27', function() {
                        console.log('escape key - clear the drag/drop operation');
                    });
                })
                .on('dragend', function(event) {
                    self.$('article').removeClass('dragging');
                    event.target.classList.remove('moving', 'draggable');    

                    // snap back to original position if we don't drop it
                    event.target.style.webkitTransform =
                    event.target.style.transform =
                    'translate(0)';
                    event.target.setAttribute('data-x', 0);
                    event.target.setAttribute('data-y', 0);

                    // event.currentTarget.classList.remove('draggable');
                    // event.currentTarget.classList.remove('moving');            
                });

            interact(moveables)
              .dropzone({
              manualStart: false,
              overlap: 'pointer',
                ondrop: function (event) {
                    var dropzoneElement = event.target;
                    var originalDraggable = event.relatedTarget;
                    
                    var $targetEl = self.$(dropzoneElement);
                    self.clone.classList.remove('draggable');
                    $targetEl.before(self.clone);
                    originalDraggable.remove();

                    dropzoneElement.classList.remove('drop-target');
                    if(!dropzoneElement.classList.length) {
                        dropzoneElement.removeAttribute('class');
                    }
                    $(dropzoneElement).velocity('stop', true).velocity({ marginTop: 0 }, {
                      duration: 140
                    });    

                },
                ondragenter: function(event) {
                    console.log('dragenter!');
                    var draggableElement = event.relatedTarget,
                    dropzoneElement = event.target;
                    dropzoneElement.classList.add('drop-target');             
                    $(dropzoneElement).velocity('stop', true).velocity({ marginTop: 84 }, {
                      duration: 140
                    });

                },
                ondragleave: function(event) {
                    var draggableElement = event.relatedTarget,
                    dropzoneElement = event.target;

                    dropzoneElement.classList.remove('drop-target');
                    if(dropzoneElement.classList.length) {
                        console.log(dropzoneElement.classList.length);
                        console.log('there are still classes');
                    } else {
                        console.log('there are no more classes, kill the attribute');
                        dropzoneElement.removeAttribute('class');
                    }
                    $(dropzoneElement).velocity('stop', true).velocity({ marginTop: 0 }, {
                      duration: 140
                    });                    
                                           
                }
              });
     
              function dragMoveListener (event) {
                var target = event.target,
                    // keep the dragged position in the data-x/data-y attributes
                    x = (parseFloat(target.getAttribute('data-x')) || 0) + event.dx,
                    y = (parseFloat(target.getAttribute('data-y')) || 0) + event.dy;

                // translate the element
                target.style.webkitTransform =
                target.style.transform =
                  'translate(' + x + 'px, ' + y + 'px)';

                // update the posiion attributes
                target.setAttribute('data-x', x);
                target.setAttribute('data-y', y);
              }

              window.dragMoveListener = dragMoveListener;

            // interact.dynamicDrop(true);

        },       
        
        fetchFromEmbedInput: function() {
            var self = this;
            var $embedInput = $('.mediaEmbedInput');
            var embedString = $embedInput.val();
            var url = '/a/api/media_embed';
            // $embedInput.before(self.loader);
            var storyId = this.postModel.id || null;
            
            console.log('embed string: ' + embedString);

            $.ajax({
                url: url,
                type: 'POST',
                data: {
                    embedstring: embedString,
                    storyid: storyId
                },
                success: function(response) {
                    console.log(response);
                    if(response.error) {
                        self.showInsertError(response.msg);
                        return;
                    }
                    if(response) {
                        if(response.type==='tweet') {
                            self.trigger('reinitTwitter');        
                        }
                    }
                    console.log('success!');
                    self.placeMedia(response);
                },
                error: function(response) {
                    self.showInsertError(response.msg);
                    return;
                },
            }).always(function() {
                self.$('.loaderBox').remove();
            });

        },

        showInsertError: function(error) {
            console.log('show insert error please');
            this.insertErrorVisible = true;
            var self = this;
            var $errorEl = $('.insertError');
            $errorEl.html(error).velocity('stop', true).velocity('transition.expandIn', 80);
            var wait = setTimeout(function() { 
                if(self.insertErrorVisible) {
                    self.hideInsertError();
                }
            }, 5000);
        },

        hideInsertError: function() {
            this.insertErrorVisible = false;
            var self = this;
            var $errorEl = $('.insertError');
            $errorEl.velocity('stop', true).velocity('reverse');            
            var wait = setTimeout(function() { 
                $errorEl.html('');
            }, 80);
        },

        embedKeyup: function(e) {
            e.preventDefault();
            var code = e.charCode || e.keyCode || e.which;
            if(code === 13) {
                this.fetchFromEmbedInput();
            }
        },
        
        toggleSpill: function(e) {
            console.log('toggle spill...');
            var $btn = $(e.currentTarget);
            var id = $btn.data('id');
            var timeOut = 120;
            var marginLeft, marginRight;
            var $figure = $('figure[data-id=' +
                id +
                ']');
            var embedModel = this.embedsCollection.get(id);
            var spilt = embedModel.get('spill');
            if(embedModel.get('spill')) {
                marginLeft = marginRight = 0;                
                console.log('spilt; bring it back in');
                $figure.removeClass('spill');   
                spilt = false;
                var wait1 = setTimeout(function() { 
                    $btn.removeClass('active');
                }, timeOut);
            } else {
                marginLeft = marginRight = -120;   
                console.log('not spilt; spill it');
                spilt = true;
                var wait2 = setTimeout(function() { 
                    console.log('go');
                    $btn.addClass('active');
                }, timeOut);
            }
            $figure.velocity('stop', true).velocity({ marginLeft: marginLeft, marginRight: marginRight }, {
              duration: timeOut
            });            
            embedModel.set('spill', spilt);
        },

        preProcessEmbeds: function() {
            var self = this;
            var allEmbeds = self.embedsCollection.models || [];

            if(allEmbeds && allEmbeds.length) {
                this.storyEmbedEditTmpl.done(function(tmpl) {
                    console.log(allEmbeds);
                    var length = allEmbeds.length;
                    var toPrune = [];
                    if(length) {
                        for(var i=0, embed, $inline, $editable ; i<length ; ++i) {
                            embed = allEmbeds[i];
                            console.log(embed.id);
                            if(!embed.id) { console.log('no id?'); console.log(embed);}
                            $inline = self.$('figure[data-id=' + embed.id + ']');
                            if($inline.length) {
                                $editable = $(tmpl(_.extend(embed.toJSON(), {
                                    spill: embed.get('imageType') === 'spill'
                                })));
                                $inline.replaceWith($editable);
                            } else { toPrune.push(embed); } // remove stray embeds
                        }
                    }
                    if(toPrune && toPrune.length) {
                        for(var i=0, embed ; i<toPrune.length ; ++i) {
                            embed = toPrune[i];
                            console.log('remove ' + embed.id + ' from collection');
                            self.embedsCollection.remove(embed);
                        }
                    }
                    self.$('.tip').tooltip('destroy').tooltip();
                });
            }
        },

        postProcessEmbeds: function($body) {
            // clean up, replace editable figures on endEdit
            // note: we're parsing a clone of the body if this is triggered by a executeSave()
            console.log('---------------- $body is ' + $body);
            var self = this;
            var allEmbeds = self.embedsCollection.models || {};  
            var $rogueImgs = $body.find('.storyBody img').not('figure img');
            console.log('embeds collection?'); console.log(allEmbeds);

            var embedsPostProcessed = new Promise(function(resolve, reject) {              

                    self.storyEmbedTmpl.done(function(tmpl) {
                        var length = allEmbeds.length;
                        if(length) {
                            for(var i=0, embed, $editable, $normalEmbed ; i<length ; ++i) {
                                embed = allEmbeds[i];
                                $editable = $body.find('figure[data-id=' + embed.id + ']');
                                if($editable.length) {
                                    $normalEmbed = $(tmpl(_.extend(embed.toJSON(), {
                                        spill: embed.get('imageType') === 'spill'
                                    })));
                                    $editable.replaceWith($normalEmbed);
                                } 
                            }
                        }
                        resolve({ 'body': $body} );
                    });

                });  
                console.log('about to return true');
                return embedsPostProcessed;                                           

            // // clear out rogue images, spacers    
            // var $firstSpacerBeforeImage = $body.find('.spacerBeforeImage:first-child');
            // if($firstSpacerBeforeImage.length && $firstSpacerBeforeImage.text().replace(/^\s+|\s+$/g, '') === '') {
            //     $firstSpacerBeforeImage.remove();
            // }
            // if($rogueImgs.length) {
            //     $.each($rogueImgs, function(index, el) {
            //         var $el = $(el);
            //         if($el.parent().is('figure')) {
            //             $el.parent().remove();
            //         } else {
            //             $el.remove();
            //         }
            //     });
            // }  

        },
                
        startUpload: function(e) {
            console.log('kickoff upload');
            this.setupImageUpload();
            this.$('.storyMediaDropZone').click();
        },

        insertErrorAlert: function(msg) {
            suiteio.notify.alert({
                msg: msg
                });
        },

        setupImageUpload: function() {
            var self = this;
            var storyId = this.postModel.id || null;
            this.imgDropzone && this.imgDropzone.destroy();
            this.imgDropzone = new Dropzone(".storyMediaDropZone", { url: "/a/api/image_upload", paramName: "image", maxFilesize: 16 });

            this.imgDropzone.on("sending", function(file, xhr, formData) {
                self.activeStoryUpload = true;
                // append some required values to the POST data
                formData.append('csrfmiddlewaretoken', suiteio.csrf);
                formData.append('storyid', storyId);
                var $loader = $('<figure class="plain image-uploading-shell imageUploadingShell" contenteditable="false"></figure>');
                    // Inject the figure uploading shell
                    if(self.$selectedHotspot && self.$selectedHotspot.length) {
                        self.$selectedHotspot.replaceWith($loader);
                    } else if (self.$clickedImageTargetEl && self.$clickedImageTargetEl.length) {
                        self.$clickedImageTargetEl.before($loader);
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
                self.placeMedia(response);
                $('.storyMediaDropZone').html('');
            });
        },
        
        addEmbed: function(mediaObject) {
            var self = this;
            this.embedsCollection.add(mediaObject);
        },

        placeMedia: function(embedObject) {
            console.log(embedObject);
            var $insertTarget = this.insertTarget;
            console.log($insertTarget);
            var self = this, $toPlace;
            var mediaObject = embedObject.media;
            var mediaType = mediaObject.type || '';

            var $toPlace;
            self.closeMediaInsert();

            // add to Backbone collection
            self.addEmbed(mediaObject);

            // build the embed html
            self.storyEmbedEditTmpl.done(function(tmpl) {
                $toPlace = $(tmpl(mediaObject));
            });
            
            // where should we put it?                
            if (!$insertTarget) {
                this.$('.storyBody').append($toPlace);
            } else {
                if(this.insertBefore) {
                    console.log('inserting before');
                    $insertTarget.before($toPlace);
                } else {
                    console.log('inserting after');
                    $insertTarget.after($toPlace);
                }
            }
            this.trigger('addedEmbed');            
            if(mediaType=='instagram') {
                window.instgrm.Embeds.process();
            } else if(mediaType=='tweet') {
                self.trigger('reinitTwitter');
            }  

            if($toPlace.is(':last-child') || !self.$('.storyBody').length) {
                self.$('.storyBody').append('<p><br/></p>')
            }     

        },

        captionKeyup: function(e) {
            var self = this;
            var embedId = $(e.currentTarget).closest('figure').data('id');
            var code = e.charCode || e.keyCode || e.which;
            var timeout = 700;
            if (this.captionDoneTyping) {
                clearTimeout(this.captionDoneTyping);
            }
            if(code === 27) { return; }
            // is this a keypress we care about?
            if(code >= 90) { return; }

            this.captionDoneTyping = setTimeout(function() { 
                self.updateCaption(embedId);
            }, timeout);
        },

        updateCaption: function(embedId) {
            console.log('updating caption for ' + embedId);
            var self = this;
            var $container = this.$('.editFigcaption[data-id=' + embedId + ']');
            var changed = false;
            var embedModel = this.embedsCollection.get(embedId);
            var modelCaption = embedModel.get('caption');
            var caption = $container.find('.captionEdit').val();
            console.log('old caption: ' + modelCaption);
            console.log('new caption: ' + caption);            
            if(caption != modelCaption) {
                embedModel.set('caption', caption);
            }            
        },

        toggleImgCreditEdit: function(e) {
            var self = this;
            var embedId = $(e.currentTarget).data('id');
            var $container = this.$('.imageCreditContainer[data-id=' + embedId + ']');
            var changed = false;
            var embedModel = this.embedsCollection.get(embedId);
            var modelCredit = embedModel.get('embedObject').credit;
            var modelCreditLink = embedModel.get('embedObject').creditLink;
            var credit, creditLink, attrs;
            
            var creditOff = function() {
                credit = $container.find('.credit').val();
                creditLink = $container.find('.creditLink').val();

                if(credit != modelCredit || creditLink != modelCreditLink) {
                    embedModel.set({
                        embedObject: {
                            'credit': credit,
                            'creditLink': creditLink
                        }
                    });
                }
                self.$('.creditLabel').off();
                $container.removeClass('active').off();
                self.stopListening(suiteio.keyWatcher);                    
            }
            var creditOn = function() {
                $container.addClass('active');
                self.listenToOnce(suiteio.keyWatcher, 'keydown:27', function() { creditOff() });
                $('.shell').on('click', function(e) { creditOff(); });
                $container.on('click', function(e) { e.stopPropagation(); return; });
                self.$('.creditLabel').on('click', function(e) { $(e.currentTarget).closest('.creditField').find('input').focus(); })
            }

            if($container.hasClass('active')) {
                console.log('already active!');
                creditOff();
            } else {
                creditOn();
            }
        },          

        deleteEmbed: function(e) {
            //Dom action bound method
            var self = this;
            var embedId = $(e.currentTarget).data('id');
            var $figureToDelete = this.$('figure[data-id='+embedId+']');
            var $figureSpacer = $figureToDelete.prev('.spacerBeforeImage');
            console.log('embedId: ' + embedId);
            var embedModel = this.embedsCollection.get(embedId);
            this.embedsCollection.remove(embedModel);
            $figureToDelete.remove();
            self.trigger('deletedEmbed');     
        },
        
        destroy: function() {
            var self = this;
            this.imgDropzone && this.imgDropzone.destroy();
            autosize.destroy(document.querySelectorAll(self.$('.captionEdit')));
            document.removeEventListener('dragstart', false);            
            interact(this.moveables).unset();

            // this.postProcessImages();//but no sync
            Backbone.View.prototype.destroy.apply(this, arguments);
        }

    });
    return PostMediaView;
});