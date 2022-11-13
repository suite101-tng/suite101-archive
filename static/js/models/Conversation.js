define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'models/PostEmbedResource',
    'models/PagingCollection'
],
function(
    $,
    Backbone,
    _,
    suiteio,
    PostEmbedResource,
    PagingCollection
) {
    'use strict';
    var PostEmbed = {};
    PostEmbed.model = PostEmbedResource.model.extend({
        urlRoot: '/api/v1/post_embed/',
        defaults: function() {
            return _.extend({}, PostEmbedResource.model.prototype.defaults);
        }
    });
    PostEmbed.collection = Backbone.Collection.extend({
        model: PostEmbed.model
    });

    var Post = Backbone.Model.extend({
        urlRoot: '/api/v1/post/',

        defaults: {
            suites: [],
            members: []
        },
    });

    var PostCollection = PagingCollection.collection.extend({
        model: Post,
        urlRoot: '/api/v1/post/',
        comparator: function(a,b) {
            return (a.get('created') > b.get('created'))? 1 : -1;
        },

        initialize: function(data, options) {
            PagingCollection.collection.prototype.initialize.apply(this, arguments);
            this.chatId = options.chatId;
        },

        url: function() {
            var url = PagingCollection.collection.prototype.url.apply(this, arguments),
                querySym = '?';
            if(this.chatId) {
                if(url.indexOf('?') >= 0) {
                    querySym = '&';
                }
                url = url + querySym + 'chat=' + this.chatId;
            }
            return url;
        },

    });

    var ConversationModel = Backbone.Model.extend({

        urlRoot: '/api/v1/conversation/',

        defaults: {
            members: []
        },

        initialize: function(attr, options) {
            this.set('posts', this._setupPostsCollection(attr));
            if(options){
                this.newonclient = options.newonclient;
            }
        },

        url: function() {
            if(this.get('resourceUri')) {
                return this.get('resourceUri');
            } else if (this.id) {
                return this.urlRoot + this.id + '/';
            } else {
                return this.urlRoot;
            }
        },

        processAttributes: function(attrs, doSet) {
            var data = _.extend({}, attrs);
            
            if(data.embeds) {
                this.embedsCollection = new PostEmbed.collection(data.embeds);
            } else {
                this.embedsCollection = new PostEmbed.collection();
            }            
            if(doSet) {
                this.set({
                    publish: data.publish
                }, {silent: true});
            }
            return data;
        },
        
        setConversationAttributes: function(attributes){
            this.set(attributes);
        },

        // deleteChat: function(id, uid) {
        //     var url = '/api/v1/chat/', self = this;
        //     if(!uid === this.get('owner').id) {
        //         suiteio.notify.alert({ msg: 'you are not the chat owner!', delay: 1000 });
        //         return false;
        //     }
        //     return $.ajax({
        //         url: url + id + '/',
        //         type: 'delete',
        //         data: JSON.stringify({
        //             chatId: id 
        //         }),
        //         success: function() {
        //             self.destroy();
        //             self.trigger('delete');
        //         }
        //     });
        // },

        inviteThroughEmail: function(email, message) {
            var url = '/api/v1/conv_invite/',
                self = this,
                _message = message || null;
            return $.ajax({
                url: url,
                type: 'POST',
                contentType: 'application/json',
                dataType: 'json',
                data: JSON.stringify({
                    conversation: this.get('resourceUri'),
                    message: _message,
                    email: email
                })
            });
        },


        addMember: function(userId) {
            var url = '/api/v1/conv_member/', self = this;
                return $.ajax({
                    url: url,
                    type: 'POST',
                    contentType: 'application/json',
                    dataType: 'json',
                    data: JSON.stringify({
                        user: { pk: userId} ,
                        conversation: { pk: this.id }
                    }),
                    success: function(response) {
                    }
                });
            return false;
        },

        removeMember: function(id, uid) {
            var url = '/api/v1/conv_member/', self = this,
                memberIds = _.pluck(this.get('members'), 'id');
            if(uid === this.get('owner').id ||
                memberIds.length === 1 ||
                memberIds.indexOf(id) < 0)
            {
                return false;
            }
            return $.ajax({
                url: url + id + '/',
                type: 'delete',
                success: function() {
                    var newmembers = _.filter(self.get('members'), function(member) {
                        if(member.id === id) {
                            self.checkedUserUri[member.user.resourceUri] = false;
                            return false;
                        }
                        return true;
                    });
                    self.set('members', newmembers);
                }
            });
        },

        findNeighbours: function(query) {
            console.log('trying to findNeighbours');
            var url = '/u/api/neighbours' + this.id,
                q = query || '';
            return $.ajax({
                url: url,
                type: 'get',
                data: {
                    q: q,
                    objtype: 'conv'
                }
            });
        },

        getPost: function(postId) {
            var posts = this.get('posts');
            if(!posts) { return false; }
            return _.findWhere(posts, {id: postId});
        },

        getLatestPosts: function() {
            var self = this;
            var currentTimeStamp = self.get('currentTimeStamp');
            if(this.postsCollection && this.postsCollection.length) {
                this.postsCollection.getLatestMessages(currentTimeStamp).done(function(response) {
                    if(response && response.objects.length) {
                        var posts = [];
                        // self.set({ currentTimeStamp: response.objects[response.objects.length-1].created });
                        for(var i=0, l=response.objects.length, post ; i<l ; ++i) {
                            post = response.objects[i];
                            if(!self.postsCollection.findWhere({ id: post.id })) {
                                // only add if we need it!
                                posts.push(post);
                            } 
                        }
                        // do we still have posts after excepting existing ones?
                        if(posts.length) {  
                            self.trigger('add:posts', posts, false, true); 
                        }
                    } 
                });
            }
        },

        // addPost: function(post, replyTo) {
        //     var url = '/api/v1/post/', self = this;
        //     var data = {
        //         conversation: this.get('resourceUri'),
        //         post: post,
        //     };
        //     if(replyTo) {
        //         data.replyTo = replyTo;
        //     }
        //     if(!post || post === '' || post.match(/^\s+$/ig)) { return false; }
        //     return $.ajax({
        //         url: url,
        //         type: 'POST',
        //         contentType: 'application/json',
        //         dataType: 'json',
        //         data: JSON.stringify(data),
        //         success: function(post) {
        //             if(post) {
        //                 self.postsCollection.add(post);
        //                 self.get('posts').push(post);
        //             }
        //         }
        //     });
        // },

        getOlderPosts: function() {
            var self = this;
            if(this.postsCollection && !this.postsCollection.bottomed) {
                return this.postsCollection.getNextPage().done(function(collection, response) {
                    self.set('posts', self.postsCollection.toJSON());
                    self.trigger('add:posts', response.objects, true);
                });
            }
            return false;
        },

        deletePost: function(id) {
        },

        parse: function(attrs) {
            attrs.posts = this._setupPostsCollection(attrs);
            return attrs;
        },

        _setupPostsCollection: function(attrs) {
            var posts = []; 
            if(attrs.posts) {
                this.postsCollection = new PostCollection(attrs.posts, {convId: attrs.id, startPage: 1, nextUrl: attrs.postsNextUrl});
                posts = this.postsCollection.toJSON();
            }
            return posts;
        }
    });

    var ConversationCollection = PagingCollection.collection.extend({
        urlRoot: '/api/v1/post/',
        model: ConversationModel,
        initialize: function(data, options) {
            PagingCollection.collection.prototype.initialize.apply(this, arguments);
            var _options = _.extend({}, options);
        },

        url: function() {
            var _url = PagingCollection.collection.prototype.url.apply(this, arguments);
            return _url;
        }
    });

    return {
        postModel: Post,
        model: ConversationModel,
        collection: ConversationCollection
    };
});