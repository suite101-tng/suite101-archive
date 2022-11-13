// PostCreateView  
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'views/PostEditView'
], function(
    $,
    Backbone,
    _,
    suiteio,
    PostEditView
) {
    'use strict';
    var PostCreateView =  PostEditView.extend({

        events: function() {
            return _.extend({
                'click .publishMiniStory': 'publishMiniStory'
                
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            this.storyMiniCreateTmpl = suiteio.templateLoader.getTemplate('story-inline-create', ['story-edit-controls']);            
            this.storyTeaserTmpl = suiteio.templateLoader.getTemplate('story-teaser');       
            this.$el = options.el;
            this.model = options.model;
            console.log(this.model);

            this.viewname = 'postcreateview';
            this.parentId = options.parentId;
        },
        
        render: function() {
            console.log('rendering PostCreateView');
            var self = this;
            this.storyMiniCreateTmpl.done(function(tmpl) {
                var context = {
                    author: suiteio.loggedInUser
                }
                var $miniCreatePane = $(tmpl(context));
                self.$el.prepend($miniCreatePane);
                // self.setupEditor();
                self.setupEdit();
                self.trigger('inlineCreateStarted');
            });
        },

        publishMiniStory: function() {
            var self = this;
            this.saveMiniStory(true);         
        },

        renderNewStory: function() {
            var self = this;
            console.log('render this story please');
        },
        
        destroy: function() {           
            Backbone.View.prototype.destroy.apply(this, arguments);
        }

    });
    return PostCreateView;
});