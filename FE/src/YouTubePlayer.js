// src/YouTubePlayer.js

import React from 'react';

const YouTubePlayer = ({ video }) => {
  // if (!video) {
  //   return (
  //     <div style={{ padding: '20px', color: '#888', textAlign: 'center' }}>
  //       마커를 클릭하면 관련 영상이 재생됩니다.
  //     </div>
  //   );
  // }

  const videoSrc = `https://www.youtube.com/embed/${video.id}?start=${video.start}&autoplay=1&mute=1`;

  return (
    <div className="youtube-player" style={{ width: '95%', height: 'auto', padding: '10px'}}>
      <iframe
        width="100%"
        height="415px"
        src={videoSrc}
        title="YouTube video player"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
      ></iframe>
    </div>
  );
};

export default YouTubePlayer;