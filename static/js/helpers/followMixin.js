define([
    'jquery',
    'underscore',
    'suiteio'
], function(
    $,
    _,
    suiteio
) {
    'use strict';
    var followUnfollowAjax = function(options) {
        var $followButton = $(options.e.currentTarget),
            followUrl = options.followUrl,
            unfollowUrl = options.unfollowUrl,
            url = '',
            $mini = options.mini || false,
            $userFollowing = false;
        $followButton.dynamicButton({
            immediateEnable: true
        });
        if ($followButton.data('following') === 1) {
            url = unfollowUrl;
        } else {
            url = followUrl;
            $userFollowing = true;
        }
        $.ajax({
            url: url,
            type: 'POST',
            error: function(response) {
                if(parseInt(response.status, 10) === 403) {
                    suiteio.fireLoginModal(window.location.pathname);
                }
            },
            success: function() {
                if (!$followButton.data('following') || $followButton.data('following') === 0) {
                    $followButton.data('following', 1);
                    if($mini) {
                        $followButton.addClass('following');
                    } else {
                        $followButton.find('.followText').text('Following');
                    }
                } else {
                    $followButton.data('following', 0);
                    if($mini) {
                        $followButton.removeClass('following');
                    } else {
                        $followButton.find('.followText').text('Follow');
                    }
                }
                // return $userFollowing;
            }
        }).always(function() {
            $followButton.dynamicButton('revert');
        });
        console.log('$userFollowing: ' + $userFollowing);     
        return $userFollowing;
    };
    
    return {
        'followUnfollowAjax': followUnfollowAjax
    };
});