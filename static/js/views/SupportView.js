// SupportView
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'lib/underwood',
    'views/PagedListView',
    'taggle'
], function(
    $,
    Backbone,
    _,
    suiteio,
    Underwood,
    PagedListView,
    Taggle
) {
    'use strict';
    var SupportView = Backbone.View.extend({
        events: function() {
            return _.extend({
                // 'click .toggleNotifSend': 'toggleAccrualNotify'
                'click .acceptRejectInvite': 'suiteInviteAcceptReject',
                'show.bs.tab .notifTab[data-toggle="tab"]': 'tabChange'
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function (options) {
            var self = this;
            this.supportQuestionTmplPromise = suiteio.templateLoader.getTemplate('support-question');
            this.feedType = 'all'
            this.utilityUrl = '/admin/api/support_edit';
            this.urlRoot = '/support'
            this.$listViewEl = options.el || '';
            this.setupSupportListView();
            this.questionEditors = {};
            this.createNewActive = false;
        },

        setupSupportListView: function(fetchFirst) {
            fetchFirst = fetchFirst || false;
            var self = this;
            var url = this.urlRoot;
            console.log('url: ' + url);
            var $listViewEl = $('.supportDetailView');
            this.supportQuestionsListView && this.supportQuestionsListView.destroy();
            this.supportQuestionsListView = new PagedListView({
                el: $listViewEl,

                firstPage: fetchFirst,
                url: url,
                templateName: 'support-question',
                name: 'supportqs'
            });

            self.listenToOnce(self.supportQuestionsListView, 'listViewReady', function() {
                self.supportQuestionsListView.fetch();
            });
            self.listenTo(self.supportQuestionsListView, 'listViewFiltered', function(namedFilter) {
                namedFilter = namedFilter || '';
                self.supportQuestionsListView.fetch();
            });             
            self.listenTo(self.supportQuestionsListView, 'noListViewResults', function() {
                console.log('nothing!!!!!!');
                var userName = '';
                if(suiteio.loggedInUser) {
                    userName = suiteio.loggedInUser.get('firstName') || suiteio.loggedInUser.get('fullName');
                }
                self.$('.supportDetailView .paginatedList').html('<div class="centered no-notifs noNotifs">Good news and bad news, ' + userName + '. You have no new notifications to deal with.');
            });
        },

        startEdit: function(e) {
            var $target = $(e.currentTarget);
            var $question = $target.closest('.supportQuestion');
            var $controls = $question.find('.supportQuestionControls');
            var questionId = $question.data('id') || '';
            this.activeEditingModel = this.supportQuestionsListView.collection.findWhere({id: questionId});

            $question.addClass('active');
            $controls.velocity("transition.slideDownIn", 200);

            // var activeSiblings = $question.siblings('.active');
            // if(activeSiblings) {
            //     for(var i=0, l=activeSiblings.length, item ; i<l ; ++i) {
            //         item = $(activeSiblings[i]);
            //         this.endEdit(item);
            //     }
            //  }            

            this.setupQuestionEditors($question);
            this.setupQuestionTags($question);
        },

        endEdit: function($question) {
            this.activeEditingModel = null;
            this.createNewActive = false;
            $question.removeClass('active');
            var $controls = $question.find('.supportQuestionControls');
            if(this.questionTagsInput && this.questionTagsInput.length) {
                this.questionTagsInput.destroy();
            }
            this.destroyQuestionEditors();
            this.setupQuestionTags($question);
            $controls.velocity("transition.slideUpOut", 200);
            if($question.hasClass('newSupportQuestion')) {
                $question.remove();
            }
        },

        setupQuestionEditors: function($question) {
            var $answerEl = $question.find('.answer');
            var $titleEl = $question.find('.title');

            this.questionEditors['answer'] = new Underwood($answerEl, {
                placeholder: {
                    hideOnClick: false,
                    text: 'Answer the question here...'
                },  
                autoLink: true,
                toolbar: {
                    updateOnEmptySelection: true,
                    buttons: [
                        'anchor',
                        'bold',
                        'italic',
                        'strikethrough',
                            'spacer1',
                        'h2',
                        'quote',
                        'unorderedlist'
                        ]
                },
                spellcheck: false,
                imageDragging: false,
                fileDragging: false,
                anchorPreview: true,
            });

            this.questionEditors['title'] = new Underwood($titleEl, {
                toolbar: false,
                disableReturn: true,   
                spellcheck: false,                 
                placeholder: {
                    hideOnClick: false,
                    text: 'How will the observation of gravitational waves affect astrophysics?'
                }
            });
        },

        destroyQuestionEditors: function() {
            var self = this;
            var eds = ['title', 'answer'];
            for(var ed, i = 0, l = eds.length ; i < l ; i += 1) {
                ed = eds[i];
                self.questionEditors[ed] && self.questionEditors[ed].destroy();
            }
            this.questionEditors = {};
        },

        setupQuestionTags: function($question) {
            var self = this;
            var tagList = [];
            var $existingTags = [];
            this.editingTagArray = [];
            var $questionTagEdit = this.$('.questionTagEdit')[0];

            // if editing, grab any preexisting tags from the listView collection model
            if(this.supportQuestionsListView) {
                if(this.activeEditingModel) {
                    tagList = this.activeEditingModel.get('tags');
                }
            }

            if(!this.questionTagsInput) {
                this.questionTagsInput = new Taggle( $questionTagEdit, {
                    duplicateTagClass: 'tag-dup',
                    placeholder: 'Tag this post',
                    submitKeys: [188, 9, 13],
                    containerFocusClass: 'active',

                    onTagAdd: function(event, tag) {
                        self.editingTagArray.push(tag);
                    },
                    onTagRemove: function(event, tag) {
                        var i = self.editingTagArray.indexOf(tag);
                        if(i != -1) {
                            self.editingTagArray.splice(i, 1);
                        }
                    }

                });                     
            }

            this.questionTagsInput.removeAll();
            if(tagList){
                for(var i=0, l=tagList.length, tag ; i<l ; ++i) {
                    tag = tagList[i].tag;
                    self.questionTagsInput.add(tag);
                }
            }
            this.$('.questionTagEdit').find('.taggle_input').focus()
        },

        createNewSupportQuestion: function(e) {
            if(this.createNewActive) {
                var $newQuestion = this.$('.newSupportQuestion');
                this.endEdit($newQuestion);
                return;
            }
            var self = this;
            var $newQ;
            var $supportList = this.$('.supportList .paginatedList');

            this.supportQuestionTmplPromise.done(function(tmpl) {
                $newQ = $(tmpl({
                    create: true,
                    modViewing: true
                }));
                $supportList.prepend($newQ);
                self.setupQuestionEditors(self.$('.newSupportQuestion'));
                self.setupQuestionTags(self.$('.newSupportQuestion'));
                self.createNewActive = true;
            });

        },

        saveSupportQuestion: function($question, togglePublish) {
            togglePublish = togglePublish || false;
            var self = this;
            var url = this.utilityUrl;
            var title = $question.find('.title').html();
            var answer = $question.find('.answer').html();
            var questionId = $question.data('id') || '';
            var tagArray = this.editingTagArray;
            var create;

            console.log('new title is ' + title);
            if($question.hasClass('newSupportQuestion')) {
                create = true;
            }            

            var tagList = JSON.stringify(tagArray);
            $.ajax({
                url: url,
                type: 'POST',
                data: {
                    pk: questionId,
                    create: create,
                    togglepublish: togglePublish,
                    title: title,
                    answer: answer,
                    tags: tagArray
                },
                success: function() {
                    console.log('support question saved!');
                    self.destroyQuestionEditors();
                    // self.questionTagsInput && self.questionTagsInput.destroy();
                    self.setupSupportListView(true);
                }
            });
        },

        saveIt: function(e) {
            var $target = $(e.currentTarget);
            var $question = $target.closest('.supportQuestion');
            this.saveSupportQuestion($question);
        },

        togglePublish: function(e) {
            var $target = $(e.currentTarget);
            var $question = $target.closest('.supportQuestion');
            this.saveSupportQuestion($question, true);
        },

        cancelSupportEdit: function(e) {
            var $target = $(e.currentTarget);
            var $question = $target.closest('.supportQuestion');
            this.endEdit($question);
        },

        clearSupplementalViews: function() {
            var views = ['supportQuestionsListView'];
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
            this.questionTagsInput && this.questionTagsInput.destroy();
            this.clearSupplementalViews();
            Backbone.View.prototype.destroy.apply(this, arguments);
        }

    });
    return SupportView;
});