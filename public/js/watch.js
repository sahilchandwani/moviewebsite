(function () {
  var video = document.getElementById('player');
  var src = document.getElementById('watch-data').getAttribute('data-src');
  if (!video || !src) return;

  video.addEventListener('contextmenu', function (e) {
    e.preventDefault();
  });

  if (window.Hls && window.Hls.isSupported()) {
    var hls = new window.Hls({ maxMaxBufferLength: 60 });
    hls.loadSource(src);
    hls.attachMedia(video);
    hls.on(window.Hls.Events.ERROR, function (event, data) {
      if (data.fatal) {
        console.error('Playback error:', data.type, data.details);
      }
    });
  } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
    // Safari has native HLS support.
    video.src = src;
  } else {
    var container = document.getElementById('player-shell');
    container.innerHTML = '<p class="alert alert--error">Your browser does not support in-site playback.</p>';
  }
})();
