//SuiteMember
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
    var SuiteMember = {};
    SuiteMember.model = Backbone.Model.extend({
        urlRoot: '/api/v1/suite_member/',
        url: function() {
            if(this.id) {
                return this.urlRoot + this.id + '/';
            } else {
                return this.urlRoot;
            }

        },
        changeMemberStatus: function(status) {
            var isEditor = (status == 'editor' ? true : false);
            var test = 'made this person normal';
            if(status=='editor') {
                test = 'made this person an editor';
            } 
            this.set({status: status, suiteEditor: isEditor, test: test}).save();
            this.trigger('memberChanged');
        },

    });
    SuiteMember.collection = Backbone.Collection.extend({
        model: SuiteMember.model,
        urlRoot: '/api/v1/suite_member/',
        url: function() {
            if(this.suiteId) {
                return this.urlRoot + '?suite=' + this.suiteId;
            }
            else if(this.memberId) {
                return this.urlRoot + '?user=' + this.memberId;
            }
            return this.urlRoot;
        },
        initialize: function(data, options) {
            if(options) {
                this.suiteId = options.suiteId;
                this.memberId = options.memberId;
            }
        },
        removeThisUser: function(id) {
            var self = this;
            var removeThisModel = self.get(id);
            if(removeThisModel) {
                if(!removeThisModel.get('owner')){
                    return removeThisModel.destroy();
                }
            }
        },
        parse: function(response) {
            if(response.objects) {
                return response.objects;
            } else {
                return response;
            }
        }
    });
    return SuiteMember;
});