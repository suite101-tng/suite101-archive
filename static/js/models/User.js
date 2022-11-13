//User
define([
    'jquery',
    'underscore',
    'backbone',
    'models/PagingCollection',
    'suiteio'
], function(
    $,
    _,
    Backbone,
    PagingCollection,
    suiteio
) {
    'use strict';

    var UserModel = Backbone.Model.extend({

        urlRoot: '/api/v1/user_mini/',

        defaults: {},

        initialize: function(attrs) {
            if(attrs && attrs.slug && !attrs.resourceUri) {
                this.set({resourceUri: this.url()});
            }
        },

        validate: function(attrs) {
        if(attrs.fullBio) {
            if(attrs.fullBio.length > 140) {
                console.log('bio is more than 140...');
            }
        }

        },

        setUserAttributes: function(attributes){
            this.set(attributes);
        },

        checkSetByline: function(byline) {
            this.set('byLine', byline);
        },    

        checkSetFullBio: function(fullBio) {
            this.set('fullBio', fullBio);
        },

        url: function() {
            if(this.get('resourceUri')) {
                return this.get('resourceUri');
            } else if(this.get('slug')) {
                return this.urlRoot + this.get('slug') + '/';
            } else {
                return this.urlRoot;
            }
        },

    });
    var UserCollection = Backbone.Collection.extend({model: UserModel});
    return {
        model: UserModel,
        collection: UserCollection
    };
});