//SuiteRequest
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
    var SuiteRequest = {},
        PENDING = 'pending',
        ACCEPTED = 'accepted',
        REJECTED = 'rejected';
    SuiteRequest.model = Backbone.Model.extend({
        urlRoot: '/api/v1/suite_request/',
        url: function() {
            if(this.id) {
                return this.urlRoot + this.id + '/';
            } else {
                return this.urlRoot;
            }
        },
        acceptRequest: function() {
            var status = this.get('status');
            if(status !== ACCEPTED) {
                return this.save({status: ACCEPTED});
            }
        },
        ignoreRequest: function() {
            var status = this.get('status');
            if(status !== REJECTED) {
                return this.save({status: REJECTED});
            }
        }
    });
    SuiteRequest.collection = Backbone.Collection.extend({
        model: SuiteRequest.model,
        urlRoot: '/api/v1/suite_request/',
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
        removeThisRequest: function(id) {
            var removeThisModel = this.get(id);
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
    return SuiteRequest;
});