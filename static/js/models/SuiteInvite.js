//SuiteInvite
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
    var SuiteInvite = {};
    SuiteInvite.model = Backbone.Model.extend({
        urlRoot: '/api/v1/suite_invite/',
        url: function() {
            if(this.id) {
                return this.urlRoot + this.id + '/';
            } else {
                return this.urlRoot;
            }

        }
    });

    SuiteInvite.collection = Backbone.Collection.extend({
        model: SuiteInvite.model,
        urlRoot: '/api/v1/suite_invite/',
        url: function() {
            if(this.suiteId) {
                return this.urlRoot + '?suite=' + this.suiteId + '&status=pending';
            }
            return this.urlRoot;
        },
        initialize: function(data, options) {
            if(options) {
                this.suiteId = options.suiteId;
            }
        },

        removeThisInvite: function(id) {
            var removeThisModel = this.get(id);
            console.log('trying to remove ' + id);
            return removeThisModel.destroy();
        },
        parse: function(response) {
            if(response.objects) {
                return response.objects;
            } else {
                return response;
            }
        }
    });
    return SuiteInvite;
});