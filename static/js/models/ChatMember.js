//ChatMember
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
    var ChatMember = {};
    ChatMember.model = Backbone.Model.extend({
        urlRoot: '/api/v1/chat_member/',
        url: function() {
            if(this.id) {
                return this.urlRoot + this.id + '/';
            } else {
                return this.urlRoot;
            }

        },
        // todo: block, remove, revoke email invite

        // changeMemberStatus: function(status) {
        //     var isEditor = (status == 'editor' ? true : false);
        //     var test = 'made this person normal';
        //     if(status=='editor') {
        //         test = 'made this person an editor';
        //     } 
        //     this.set({status: status, suiteEditor: isEditor, test: test}).save();
        //     this.trigger('memberChanged');
        // },

    });
    ChatMember.collection = Backbone.Collection.extend({
        model: ChatMember.model,
        urlRoot: '/api/v1/chat_member/',
        url: function() {
            if(this.chatId) {
                return this.urlRoot + '?chat=' + this.chatId;
            }
            else if(this.userId) {
                return this.urlRoot + '?user=' + this.userId;
            }
            console.log('url root is ' + this.urlRoot);
            return this.urlRoot;
        },
        initialize: function(data, options) {
            console.log('init chatmember collection');
            console.log(options);
            if(options) {
                this.chatId = options.chatId;
                this.userId = options.userId;
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
    return ChatMember;
});