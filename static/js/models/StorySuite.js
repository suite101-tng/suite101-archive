//StorySuite
define([
    'jquery',
    'underscore',
    'backbone'
], function(
    $,
    _,
    Backbone
) {
    'use strict';
    var StorySuite = {};
    StorySuite.model = Backbone.Model.extend({
        urlRoot: '/api/v1/suite_story/',
        url: function() {
            if(this.id) {
                return this.urlRoot + this.id + '/';
            } else {
                return this.urlRoot;
            }

        },
        reorder: function(order) {
            this.save({order: order}, {patch: true});
        }
    });
    StorySuite.collection = Backbone.Collection.extend({
        model: StorySuite.model,
        urlRoot: '/api/v1/suite_story/',
        url: function() {
            if(this.suiteId) {
                return this.urlRoot + '?suite=' + this.suiteId;
            }
            else if(this.storyId) {
                return this.urlRoot + '?story=' + this.storyId;
            }
            return this.urlRoot;
        },
        initialize: function(data, options) {
            if(options) {
                this.suiteId = options.suiteId;
                this.storyId = options.storyId;
            }
        },
        removeThisStory: function(storyId) {
            var story = this.findWhere({storyId: storyId});
            return story && story.destroy();
        },

        unfeatureSuite: function(id) {
            var model = this.findWhere({storyId: id});
            if(model) {
                model.set('suite_featured', null);
                model.save();
            }
        },

        featureSuite: function(id, suite) {
            var model = this.findWhere({storyId: id});
            if(model) {
                model.set('suite_featured', suite.toJSON());
                model.save();
            }
        },

        addStory: function(storyModel, suiteModel) {
            console.log('welcome to addstory');
            var model = new this.model({
                story: storyModel.get('storyResourceUri'),
                storyId: storyModel.id,
                suiteId: suiteModel.id,
                suite: suiteModel.get('resourceUri')
            });
            this.add(model);
            return model.save().done(function() {
                suiteModel.get('stories').push(storyModel.toJSON());
                suiteModel.trigger('addStory', storyModel);
            });
        },

        reorderItem: function(targetId, prevId, nextId) {
            var targetModel, prevModel, nextModel, newOrder;
            targetModel = this.findWhere({storyId: targetId});
            if(prevId) {
                prevModel = this.findWhere({storyId: prevId});
            }
            if(nextId) {
                nextModel = this.findWhere({storyId: nextId});
            }
            if(!nextModel && prevModel) {
                //it became the last item
                newOrder = Math.round(prevModel.get('order') * 1.5);
            } else if (!prevModel) {
                //it became the first item
                newOrder = Math.round(nextModel.get('order') / 2);
            } else {
                newOrder = Math.round((nextModel.get('order') + prevModel.get('order')) / 2);
            }
            targetModel.reorder(newOrder);
        },
        parse: function(response) {
            if(response.objects) {
                return response.objects;
            } else {
                return response;
            }
        }
    });
    return StorySuite;
});