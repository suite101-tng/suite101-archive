define(['jquery'], function($) {
    'use strict';
    return {
        findNeighbours: function(query,objectType,objectId) {
            console.log('trying to findNeighbours');
            var objectId = objectId || '',
                objectType = objectType || '',
                url = '/u/api/neighbours' + objectId,
                q = query || '';
            return $.ajax({
                url: url,
                type: 'get',
                data: {
                    q: q,
                    objtype: objectType
                }
            });
        },

        findMembers: function(query) {
            var url = '/api/v1/search/users/',
                q = query || '';
            return $.ajax({
                url: url,
                type: 'get',
                data: {
                    q: q
                }
            });
        },

        findMembersWithEmail: function(email) {
            var url = '/api/v1/search/users_email/',
                q = email;
            return $.ajax({
                url: url,
                type: 'get',
                data: {
                    q: q
                }
            });
        }
    }
})