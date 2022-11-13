// ModerateView
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'taggle',
    'lib/underwood'
], function(
    $,
    Backbone,
    _,
    suiteio,
    Taggle,
    Underwood
) {
    'use strict';
    var ModerateView = Backbone.View.extend({
        events: function() {
            return _.extend({
                'click .toggleNotifSend': 'toggleAccrualNotify',
                'click .shrunkEntry': 'toggleElementDetails',
                'click .royalModUpdate': 'royalModUpdate',
                'click .modTagLink': 'tagLinkCatcher',
                'keypress .modNoteEntry': 'noteKeyup'
            }, _.result(Backbone.View.prototype, 'events'));
        },
        initialize: function (options) {
            this.storyType = this.suiteType = this.userType = this.chatType = this.linkType = false;
            options = options || {};

            this.itemId = options.itemId || '';
            this.user = options.user || '';
            this.userId = options.userId || '';
            this.rootUrl = '/admin/api/mod_card';
            this.accrualNotify = false;
            this.modThisModalTmpl = suiteio.templateLoader.getTemplate('mod-this-modal', ['tag-list-item', 'mod-note']);
            this.modNoteTemplate = suiteio.templateLoader.getTemplate('mod-note');
            this.tagTmpl = suiteio.templateLoader.getTemplate('tag-list-item');
            this.tagInput = '<input class="edit-story-tags editModTags" style="display: none;" name="tags" id="tags" placeholder="Mod tags" value="" />';
        },

        fetchModCardContext: function(contenttype, contentid) {
            var self = this;
            return $.ajax({
                url: self.rootUrl,
                type: 'POST',
                data: {
                    contenttype: contenttype,
                    contentid: contentid
                }
            });
        },

        openModCard: function(options) {
            options = options || {};
            var contentId = options.contentId || '';
            var contentType = options.contentType || '';

            var self = this;
            this.fetchModCardContext(contentType,contentId).then(function(context) {
                self.modTags = context.modTags;
                self.user = context.user;
                self.object = context.object || '';
                self.modThisModalTmpl.done(function(tmpl) {
                    self.modCard = $(tmpl(context));
                    self.modCard.modal({ blur: false }); 
                    self.trigger('renderComplete');
                });
            });
        },

        afterRender: function() {
            this.setElement(this.modCard);
            this.setupModTags();
            this.setupModNotes();
        },

        setupModNotes: function() {
            var self = this;
            var $noteForm = this.$('.modNoteEntry');
            this.modNoteEditor = new Underwood($noteForm, {
                toolbar: {
                    updateOnEmptySelection: true,
                    buttons: [
                        'anchor',
                        'bold',
                        'italic'                  ]
                },
                // disableReturn: true,   
                spellcheck: false,                 
                placeholder: {
                    hideOnClick: false,
                    text: 'Type a note about this user'
                },                       
            });              
        },

        noteKeyup: function(e) {
            var code = e.charCode || e.keyCode || e.which;
            if(code === 13) {
                e.preventDefault();
                this.postModNote(e);
            }
        },

        postModNote: function(e) {
            var self = this;
            var $noteForm = this.$('.modNoteEntry');
            var message = $noteForm.html();
            var noteType = $noteForm.data('type');
            var contentId = $noteForm.data('id');
            console.log('outgoing message: ' + message);

            if(!message || message.match(/^\s+$/)) {
                suiteio.notify.alert({
                        msg:'Oops! Please type your message before trying to submit it.',
                        delay: 5000
                    });
                 $send.dynamicButton('revert');
                 this.$('.chatMessage').removeClass('obscureButt');
                return;
            }
                   
            var postNote = $.ajax({
                url: self.rootUrl,
                type: 'POST',
                data: {
                    modnote: true,
                    notetype: noteType,
                    cid: contentId,
                    msg: message
                },
                success: function(response) {
                    console.log(response);
                    if(!response) {
                        console.log('nope, nothing');
                    } else { 
                        self.renderModNotes(response);
                    }
                    self.clearModNoteInput();
                }                    
            });  

        },

        clearModNoteInput: function() {
            this.$('.modNoteEntry').html('');            
        },

        renderModNotes: function(notes, clear) {
            var self = this;
            console.log('rendering...');
            var $listContainer = this.$('.modNotesList');
            var clear = clear || false;
            if(notes && notes.length) {
                self.modNoteTemplate.done(function(tmpl) {
                    var $domFrag = $(document.createDocumentFragment());
                    for(var i=0, l=notes.length, note ; i<l ; ++i) {
                        note = notes[i];
                        $domFrag.append(tmpl(note));
                    }
                    if(clear) {
                        $listContainer.append($domFrag);
                    } else {
                        $listContainer.prepend($domFrag);
                    }
                });
            }
        },

        setupModTags: function() {
            var self = this;
            var $tagEdit = this.$('.editModTags');
            var $modTagEdit = this.$('.modTagEdit')[0];
            
            this.$('.modTagEdit').addClass('active');
            this.$('.modTags').removeClass('active');

            if(!this.tagsInput) {
                this.tagsInput = new Taggle( $modTagEdit, {
                    duplicateTagClass: 'tag-dup',
                    placeholder: 'Tag this member',
                    submitKeys: [188, 9, 13],
                    containerFocusClass: 'focused',

                    onTagAdd: function(event, tag) {
                        if(self.modTagsReady) {
                            self.updateModTags();
                        }
                    },
                    onTagRemove: function(event, tag) {
                        if(self.modTagsReady) {
                            self.updateModTags();
                        }
                    }

                });                     
            }

            this.tagsInput.removeAll();
            var tagList = this.modTags;
            if(tagList){
                for(var i=0, l=tagList.length, tag ; i<l ; ++i) {
                    tag = tagList[i].tag;
                    console.log('appending ' + tag);
                    self.tagsInput.add(tag);
                }
            }
            this.$('.modTagEdit').find('.taggle_input').focus()
            this.modTagsReady = true;
        },

        updateModTags: function() {
            var self = this;
            var tagArray = [];
            var userId = this.$('.modUserTab').data('id');
            var $tagDisplay = this.$('.modTags');
            $('.modTagEdit .taggle_list .taggle input').each(function(i, elem) {
                tagArray.push($(elem).val().trim());
            });
            var tagList = JSON.stringify(tagArray);
            var updateTags = $.ajax({
                url: self.rootUrl,
                type: 'POST',
                data: {
                    updatetags: true,
                    userid: userId,
                    tags: tagList
                },
                success: function() {
                }                    
            });            
        },

        tagLinkCatcher: function(e) {
            var $ctarget = $(e.currentTarget);
            e.preventDefault();
            e.stopPropagation();
        },

        deleteSpammy: function(e) {
            if(!suiteio.loggedInUser) { return; }
            var self = this,
                $target = $(e.currentTarget),
                $userId = $target.data('id');
            suiteio.notify.prompt({
                msg: 'Are you sure you want delete this member?'
            }).done(function(decision) {
                if(decision) {
                    var url = '/admin/api/delete_spam';
                    $.ajax({
                        url: url,
                        type: 'POST',
                        data: {
                            userid: $userId
                        },
                        success: function() {
                            suiteio.notify.alert({msg: 'Deleted!'});
                            self.showModStories();
                        }
                    });
                }
            });
        },

        toggleElementDetails: function(e) {
            var $ctarget = $(e.currentTarget);
            this.$('.shrunkEntry').not($ctarget).removeClass('open');
            $ctarget.toggleClass('open');
        },
            
        toggleFeatured: function(e) {
            var self = this;
            var $target = $(e.currentTarget);
            var $label = $target.closest('.featureThis').find('h4');
            var contentType = $target.data('type');
            var contentId = $target.data('id');
            $.ajax({
                url: self.rootUrl,
                type: 'POST',
                data: {
                    ftoggle: true,
                    ctype: contentType,
                    cid: contentId
                },
                success: function(featured) {
                    var newLabel;
                    if(!!featured) {
                        $target.addClass('checked'); 
                        newLabel = "Featured";    
                    } else {
                        $target.removeClass('checked'); 
                        newLabel = "Feature this";
                    }    
                }
            });
        },

        toggleAds: function(e) {
            var self = this;
            var $target = $(e.currentTarget);
            var $container = $target.closest('.adsToggle');
            var contentId = $target.data('id');
            $.ajax({
                url: self.rootUrl,
                type: 'POST',
                data: {
                    adstoggle: true,
                    cid: contentId
                },
                success: function(response) {
                    var newLabel;
                    if(response.show) {
                        $container.removeClass('ads-auto').addClass('ads-on');
                    } else if(response.hide) {
                        $container.removeClass('ads-on').addClass('ads-off');
                    } else {
                        if(response.autoStatus) {
                           self.$('.adsEnabledStatus').html('Enabled');
                        } else {
                            self.$('.adsEnabledStatus').html('Disabled');
                        }
                        $container.removeClass('ads-off').addClass('ads-auto');
                    }
                }
            });
        },       

        toggleApproved: function(e) {
            var $target = $(e.currentTarget);
            var url = this.rootUrl;
            var userId = this.user.id || $target.data('id');
            $.ajax({
                url: url,
                type: 'POST',
                data: {
                    toggleapproved: true,
                    userid: userId
                },
                success: function(response) {
                    if(response) {
                        $target.addClass('btn-blue').removeClass('btn-subdued').html('Approved');
                    } else {
                        $target.removeClass('btn-blue').addClass('btn-subdued').html('Probation');
                    }
                }
            });
        },

        toggleIndexed: function(e) {
            var $target = $(e.currentTarget),
                url = $target.attr('href');
            $.ajax({
                url: url,
                type: 'POST',
                data: {},
                success: function() {
                    $('.toggleIndexed').toggleClass('active dark'); 
                    if($('.toggleIndexed').hasClass('active')) {
                        $('.toggleApproval').addClass('active dark');
                    } 
                }
            });
        },

        toggleDeferral: function(e) {
            var $target = $(e.currentTarget),
                url = $target.attr('href');
            $.ajax({
                url: url,
                type: 'POST',
                data: {},
                success: function() {
                    $target.toggleClass('active dark');
                    if($('.setDefer').hasClass('active')) {
                        $('.toggleApproval').removeClass('active blue');
                    }
                }
            });
        },

        destroy: function() {
            this.modNoteEditor && this.modNoteEditor.destroy();
            Backbone.View.prototype.destroy.apply(this, arguments);
        }

    });
    return ModerateView;
});