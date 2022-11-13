define([
    'backbone',
    'underscore',
    'models/ImageResource'
], function(
    Backbone,
    _,
    ImageResource
) {
    'use strict';
    var SuiteImage = {};
    SuiteImage.model = ImageResource.model.extend({
        urlRoot: '/api/v1/suite_image/'
    });
    SuiteImage.collection = Backbone.Collection.extend({
        model: SuiteImage.model
    });
    var SuiteModel = Backbone.Model.extend({
        urlRoot: '/api/v1/suite/',

        initialize: function(attrs) {
            this.parseAttributes(attrs);
        },

        validate: function(attrs) {
            if((!attrs.name || attrs.name.match(/^\s*$/))) {
                return 'Please give your suite a name';
            }
            if(attrs.name && attrs.name.length > 140) {
                return 'Suite name is beyond the 140 characters length limit';
            }
            if(attrs.description && attrs.description.length > 240) {
                return 'Suite description is beyond the 240 characters length limit';
            }
        },

        getStoryIndex: function(storyId) {
            var index = _(this.get('stories')).pluck('id').indexOf(storyId);
            return index;
        },

        hasStory: function(storyId) {
            return (this.getStoryIndex(storyId) >= 0);
        },

        removeStory: function(storyId) {
            var index = this.getStoryIndex(storyId);
            if(index >= 0) {
                this.get('stories').splice(index, 1);//remove
            }
        },

        checkSetDescription: function(description) {
            // todo: validate length
            this.set('description', description);
        },

        checkSetAbout: function(about) {
            // todo: validate length
            this.set('about', about);
        },

        url: function() {
            if(this.id) {
                return this.urlRoot + this.id + '/';
            } else {
                return this.urlRoot;
            }
        },

        removeHeroImage: function() {
            //not quite a delete, just disassociation
            this.heroImageModel = null;
            this.set('heroImage', {});
        },

        setHeroImage: function(attrs) {
            if(!this.heroImageModel) {
                this.heroImageModel = new SuiteImage.model();
            }
            this.heroImageModel.set(attrs);
            this.set({
                heroImage: this.heroImageModel.toJSON()
            });
        },

        parseAttributes: function(attrs, doSet) {
            var data = _.extend({}, attrs);
            if(data.heroImage) {
                this.setHeroImage(data.heroImage);
            }
            return data;
        },

        parse: function(response) {
            return this.parseAttributes(response);
        }
    });
    var SuiteCollection = Backbone.Collection.extend({});
    return {
        model: SuiteModel,
        collection: SuiteCollection
    };
});