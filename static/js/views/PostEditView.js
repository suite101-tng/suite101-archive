// PostEditView.js
define([
    'jquery',
    'underscore',
    'backbone',
    'suiteio',
    'views/StoryView',
    'views/PostMediaView',
    'lib/Countable',
    'lib/underwood',
    'taggle'
], function(
    $,
    _,
    Backbone,
    suiteio,
    StoryView,
    PostMediaView,
    Countable,
    Underwood,
    Taggle
) {
    'use strict';
    var ERROR_MSG = 'There was an error processing your request, please try again later. If problem persists, refresh the page and try again.';
    var PostEditView = Backbone.View.extend({

        events: function() {
            return _.extend({
                // 'keypress .linkInput': 'linkInputKeyup', 

            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            this.viewname = 'posteditview';
            this.windowSize = suiteio.getWindowSize();
            if(suiteio.getWindowSize().width < 768) {
                this.smallScreen = true; } else { this.smallScreen = false; }

            this.model = options.model || {};
            this.noBody = this.isEmpty();   
            this.startingWordCount = this.model.get('wordCount');
            this.dirty = false;

            // to allow reversion; update snapshot on sync
            this.modelSnapshot = this.model.toJSON();
            this.listenTo(this.model, 'sync', function(model) {
                this.modelSnapshot = model.toJSON();
                this.$('.saveIt').dynamicButton('revert');
            });

            this.setupEdit(); 
            this.loader = '<div class="orbitalloader relative blue"><i class="io io-load-c io-spin"></i></div>';
            this.$('.tip').tooltip();
            this.tempStorySuiteList = '';
            this.tempOtherSuitesCount = '';
        },

        afterRender: function() {
            //noop
        },

        isDirty: function() {
            if(this.storyDeleted === true) {
                return false;
            }
            return this.dirty;
        },

        setDirtyFlag: function() {
            this.dirty = true;
            this.noBody = false;
            this.$('.saveStay').addClass('changed');
            this.$('.didSave').hide();
            this.$('.toggleEditControl').text('View'); 
        },

        removeDirtyFlag: function() {
            // reset running word counts
            this.startingWordCount = this.model.get('wordCount');
            this.wordsAddedOrRemoved = 0;
            this.dirty = false;
            this.noBody = false;
            this.$('.saveStay').removeClass('changed').addClass('saved');
            this.$('.didSave').show();
            var wait = setTimeout(function() { 
                this.$('.saveStay').removeClass('saved');
            }, 1000);
        },

        updateWordCount: function(wc) {
            var $body = self.$('.postBody');
            if(this.wc && this.wc !== wc) {
                this.setDirtyFlag();
                // set words changed for user stats
                this.wordsAddedOrRemoved = wc - this.startingWordCount;
            }
            this.wc = wc;
            if(wc) {
                switch(this.smallScreen) {
                    case true:
                        this.$('.wordCount').text(wc);
                    break;
                    default:
                        var word = (wc > 1)? 'words' : 'word';
                        this.$('.wordCount').text(wc + ' ' + word);
                    break;
                }
            } 
        },

        setupEdit: function() {
            console.log('setting up edit...');
            // TODO: get a promise back from storyparentview, set to model
            // this.model.set({storyParent: result}); // update the model

            var self = this,
                editorTools;

            var $postFormHeader = self.$('.postFormHeader').get(0);
            if(this.viewname !== 'postcreateview') {
                self.slideNavIn();
            } else {
                self.newOnClient = true;
                self.$('.editNav').velocity('stop', true).velocity({ top: 0 }, { duration: 250, easing: [ 0.19, 1, 0.22, 1 ] });                           
            }
            
            var wait = setTimeout(function() { 

                editorTools = [
                    'anchor',
                    'pre',
                    'italic',
                    'h2',
                    'quote',
                    'unorderedlist'
                ];
                self.bodyEditor = new Underwood(self.$('.postBody'), {
                    placeholder: {
                        hideOnClick: false,
                        text: 'Start writing...'
                    },           
                    toolbar: {
                        relativeContainer: $postFormHeader,
                        static: true,
                        align: 'right',
                        updateOnEmptySelection: true,
                        buttons: editorTools,
                        updateOnEmptySelection: true
                    },
                    spellcheck: false,
                    imageDragging: false,
                    fileDragging: false,
                    anchorPreview: true,
                    firstHeader: 'h2',
                    secondHeader: 'h2'
                });

                $('body').off('.storysavekeypress').on('keydown.storysavekeypress', function(e) {
                    var code = e.charCode || e.keyCode || e.which;
                    if((code === 83 && (e.ctrlKey||e.metaKey)) || code === 19) {
                        e.preventDefault();
                        self.saveEdit();
                        return false;
                    }
                });

                self.countable = Countable.live(self.$('.postBody').get(0), function(counter) {
                    self.updateWordCount(counter.words);
                });
                if(this.viewname !== 'postcreateview') {
                    self.newPost = true;
                } else {
                    self.newPost = false;
                }
                self.mediaView = new PostMediaView({
                    el: self.$el,
                    embeds: self.model.embedsCollection,
                    postModel: self.model,
                    newPost: self.newPost
                });
                self.listenTo(self.mediaView, 'saveEdit', function() {
                    self.saveEdit();
                });
                self.listenTo(self.mediaView, 'addedEmbed', function(imageId) {
                    self.setDirtyFlag();
                });
                self.listenTo(self.mediaView, 'deletedEmbed', function() {
                    self.setDirtyFlag();
                });
                self.setupTags();
                self.editing = true;
                self.$('.postBody').focus();

                self.listenTo(self.mediaView, 'reinitTwitter', function() {
                    // reinit instagram, twitter, etc:
                    twttr.widgets.load();
                });
            }, 200); // end wait
        },

        setupTags: function() {
            var self = this;
            var tagList = self.model.get('tagList') || '';
            var $existingTags = [];
            var $storyTagEdit = this.$('.postTagEdit')[0];

            if(!this.storyTagsInput) {
                this.storyTagsInput = new Taggle( $storyTagEdit, {
                    duplicateTagClass: 'tag-dup',
                    placeholder: 'Tag this post',
                    submitKeys: [188, 9, 13],
                    containerFocusClass: 'active'
                });                     
            }

            this.storyTagsInput.removeAll();
            if(tagList){
                for(var i=0, l=tagList.length, tag ; i<l ; ++i) {
                    tag = tagList[i].tag;
                    self.storyTagsInput.add(tag);
                }
            }
            this.$('.storyTagEdit').find('.taggle_input').focus();
            this.storyTagsInput.onTagAdd = function(event,tag) { console.log('added tag!!!!!!'); self.setDirtyFlag(); };
            this.storyTagsInput.onTagRemove = function(event,tag) { self.setDirtyFlag(); }

        },

        isEmpty: function() {
            if(!this.$('.postBody').html()) {
                return true;
            } else { return false; }
        },

        toggleEditAction: function() {
            var self = this;
            if(this.processingSave) {
                return;
            }
            if(this.viewname === 'posteditview') {
                if(this.isDirty()) {

                    var actionDecision = {};
                    actionDecision.title = 'Save your changes?';
                    actionDecision.mainContent = '<p>You have unsaved changes that will be lost if you don\'t click the blue thing below.</p>';

                    actionDecision.act1 = {
                        action: 'doSave',
                        text: 'Save changes'
                    };
                    actionDecision.act2 = {
                        action: 'doDiscard',
                        text: 'Discard'
                    };      
                    this.listenTo(suiteio.vent, 'doSave', function() {
                        'doSave', self.executeSave({}, true, true)
                    });
                    this.listenTo(suiteio.vent, 'doDiscard', function() {
                        self.endEdit({revert: true});
                    });
                    suiteio.genericActionModal(actionDecision);
                } else {
                    this.endEdit({revert: false});
                }
            } else {
                if(this.syncedModel) {
                    this.endEdit({reRender: true});
                } else {
                    if(this.viewname !== 'postcreateview') {
                        this.goBack();
                    } else {
                        self.trigger('stopInlineCreate');
                    }
                }
            }
        },

        slideNavOut: function() {
            $('.editNav').velocity('stop', true).velocity({ top: -64 }, { duration: 250, easing: [ 0.19, 1, 0.22, 1 ] });            
            $('.navbar').velocity('stop', true).velocity({ top: 0 }, { duration: 250, easing: [ 0.19, 1, 0.22, 1 ] });
            $('.editToggle').velocity('stop', true).velocity({ top: 0 }, { duration: 250, easing: [ 0.19, 1, 0.22, 1 ] });
        },

        slideNavIn: function() {
            $('.editNav').velocity('stop', true).velocity({ top: 0 }, { duration: 250, easing: [ 0.19, 1, 0.22, 1 ] });            
            $('.navbar').velocity('stop', true).velocity({ top: -64 }, { duration: 250, easing: [ 0.19, 1, 0.22, 1 ] });
            $('.editToggle').velocity('stop', true).velocity({ top: -64 }, { duration: 250, easing: [ 0.19, 1, 0.22, 1 ] });
        },

        endEdit: function(options) {
            var self = this;
            this.mediaView.postProcessEmbeds($storyBody);

            if(this.viewname !== 'postcreateview') {
                this.slideNavOut();
                var $storyBody = this.$('.postBody');
                $('body').removeClass('story editor-active');
                // $('.editControls').removeClass('editing');
                self.$('.editActions').remove();
                if(self.hideShowEls.length) {
                    self.$(self.hideShowEls.join(', ')).show();
                }
                if(self.showHideEls.length) {
                    self.$(self.showHideEls.join(', ')).hide();
                }
                self.$('.editNav').removeClass('active');                
            } else {
                console.log('this is inline create view - ending edit!');
                self.$('.editNav').velocity('stop', true).velocity({ top: -54 }, { duration: 140, easing: [ 0.19, 1, 0.22, 1 ] });                           
            }            

            self.$('.editArticle').removeClass('active');
            self.destroyEditors();
            self.$('.publishingControls').hide();
            self.editing = false;
            // self.mediaView.destroy();
            if(options && options.reRender === true) {
                self.render();
            }
            if(options && options.revert) {
                self.model.set(self.modelSnapshot);
            }
            self.trigger('doneEditMode', self.model);
        },

        destroyEditors: function() {
            var editor;
            if(this.editors) {
                for(var key in this.editors) {
                    editor = this.editors[key];
                    editor.destroy();
                }
                this.editors = void 0;
            }
        },

        toggleImageMode: function() {
            //pass it on..
            this.mediaView.toggleImageMode();
        },

        scrollToTags: function(e) {
            console.log('scroll to tags!');
            var $tagContainer = this.$('.tagContainer');
            $tagContainer.velocity("scroll", { 
                container: this.$('.pageWrapper'),
                duration: 800

            });
        },

        // saveEdit: function(e) {
        //     var $btn = e && $(e.currentTarget);
        //     this.executeSave({}, false, false, $btn);
        //     twttr.widgets.load();
        // },

        bodyScan: function() {
            //scan the story body, clean out unwanted attributes
            // var storyElements = this.$el.find(selector);
            var storyElements = this.$el.find('.drop-target, .draggable *');
            [].forEach.call(storyElements, function(el) {
                el.classList.remove('drop-target');
                
                if(el.classList.length) {
                        console.log(el.classList.length);
                        console.log('there are still classes');
                    } else {
                        console.log('there are no more classes, kill the attribute');
                        el.removeAttribute('class');
                    }


            });

            // var storyElements = this.$el.querySelectorAll('.drop-target');
            // for(var $elem, i=0, l=storyElements.length ; i < l ; ++i) {
            //     $elem = $(storyElements[i]);
            //     $elem.removeClass(selector);
            // }
        },

        postPost: function(e) {
            console.log('posting....');
            console.log(this.model);
            var $btn = e && $(e.currentTarget);
            this.executeSave({
                'publish': true,
                'isPublished': true,
                'isDraft': false
            }, true, false, $btn);

        },

        addPost: function(e, publish) {
            console.log('hi how are you? adding post...');
            publish = publish || true;
            var $postForm = $(e.currentTarget).closest('.postForm');
            this.executeSave(publish, $postForm);
        },

        savePost: function(e) {
            if(this.newOnClient) {
                this.addPost(e, false);
            } else {
                // sync model
            }
        },

        executeSave: function(publish, $postForm) {
            var embedsPromise,
                self = this,
                attrs,
                $bodyShadow,
                doneMsg = 'Saved';
                var $body;
                var $btn = $postForm.find('.addPost');

            if(this.processingSave) {
                console.log('eh? processing save?');
                return;
            }

            var embedsCollection = [];
            this.processingSave = true; //semaphore
            $btn.dynamicButton({immediateEnable: true});
            self.bodyScan();
                           
            this.$('.mediaInsert').remove();
            $bodyShadow = this.$('.postBody').clone();

            this.mediaView.postProcessEmbeds($bodyShadow).then(function(response) {
                $body = response.body;

                var tagArray = [];
                self.$('.postTagEdit .taggle_list .taggle input').each(function(i, elem) {
                    tagArray.push($(elem).val().trim());
                    console.log($(elem).val());
                });

                attrs = {
                    'embeds': embedsCollection,
                    'publish': publish,
                    body: self.sanitizeBody($body),
                    tag_list: JSON.stringify(tagArray),
                    wordsChanged: self.wordsAddedOrRemoved                    
                };
                self.model.set(attrs);
                self.model.save(attrs, {
                        wait: true
                    }).done(function(savedModel) {
                        self.removeDirtyFlag();
                        self.processingSave = false;
                        $btn && $btn.dynamicButton('revert');
                        console.log('synced - either render the post (if adding), or save and exit (if editing)');                    
                    }).fail(function() {
                        suiteio.notify.alert({msg: ERROR_MSG, type: 'error'});
                    }); 
                
                if(self.newOnClient) {
                    self.trigger('addPost', self.model);
                }
            
            });
  
        },

        // validateForm: function() {
        //     var error = null;
        //     if(!this.$('.postBody').html()) {
        //         error = 'Body cannot be empty';
        //         suiteio.notify.alert({
        //             msg: error,
        //             type: 'error'
        //         });
        //     }
        //     if(!this.$('header h1').text()) {
        //         error = 'Title cannot be empty';
        //         suiteio.notify.alert({
        //             msg: error,
        //             type: 'error'
        //         });
        //     }
        //     if(this.$('header h1').text()>255) {
        //         error = 'Title cannot be longer than 255 characters';
        //         suiteio.notify.alert({
        //             msg: error,
        //             type: 'error'
        //         });
        //     }
        //     if(error) {
        //         return false;
        //     } else {
        //         return true;
        //     }
        // },

        sanitizeBody: function($bodyShadow) {
            console.log($bodyShadow);
            $bodyShadow.find('.imageLoading').remove();
            $bodyShadow.contents().each(function(index, el) {
                var $el = $(el);
                if($el) {
                    $el.text().replace('<p><br></p>', '');
                    $el.text().replace('<br></p>', '');
                    if(el.nodeType === 3) {
                        $el.replaceWith($('<p>' + $el.text() + '</p>'));
                    }
                }
            });
            return $bodyShadow.html().replace(/(^\s+)|(\n)/ig, '').replace(/&nbsp;/ig, ' ');
        },

        sanitizeTitles: function(input, fillIn) {
            if(input) {
                input = input.replace(/^\s+/ig, '').replace(/\n$/g, '');
            } else {
                input = '';
            }
            if(!input && fillIn) {
                input = 'Untitled';
            }
            return input;
        },

        editArticleAction: function() {
            //dom binded action
            this.endEdit({reRender: true});
        },

        editControlAction: function(e) {
            var deferAction = $(e.currentTarget).data('deferAction');
            this.trigger('controlButtonPressed', deferAction, e);
        },

        deleteStory: function() {
            var self = this;
            var actionDecision = {};
            actionDecision.title = 'Delete this post';
            actionDecision.mainContent = '<p>Are you sure you want to permanently delete this post?</p>';

            actionDecision.act1 = {
                action: 'doDelete',
                text: 'Yes'
            };
  
            this.listenTo(suiteio.vent, 'doDelete', function() {
              self.model.destroy({
                    wait: true
                }).done(function() {
                    self.storyDeleted = true;
                    self.trigger('doneEditMode');
                    self.goBack();
                });
            });
            suiteio.genericActionModal(actionDecision);
        },

        discardStory: function() {
            var self = this;
            self.model.destroy({
                wait: true
            }).done(function() {
                self.storyDeleted = true;
                self.trigger('doneEditMode');
                self.goBack();                
            })
        },

        goBack: function() {
            if(window.history.length) {
                window.history.back();
            } else {
                window.location.href = "/";
            }
        },

        clearSupplementalViews: function() {
            var views = ['mediaView'];
            for(var view, i = 0, l = views.length ; i < l ; i += 1) {
                view = views[i];
                if(this[view]) {
                    this[view].destroy();
                    this.stopListening(this[view]);
                    this[view] = null;
                }
            }
        },        

        destroy: function() {
            if(this.editing) {
                this.slideNavOut();
                this.destroyEditors();
            }
            this.clearSupplementalViews();
            this.tagsInput && this.tagsInput.destroy();
            $('body').off('.storysavekeypress');
            this.countable.die(this.$('.postBody').get(0));
            this.model = null;
            $('body').removeClass('editor-active');
            Backbone.View.prototype.destroy.apply(this, arguments);
        }

    });
    return PostEditView;
});