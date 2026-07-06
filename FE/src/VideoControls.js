// src/VideoControls.js

import React from 'react';

const VideoControls = ({ onPrev, onNext, onLike, isLiked, isPrevDisabled }) => {
  const likeButtonStyle = {
    color: isLiked ? '#FF0000' : '#ccc',
    fontSize: '24px',
    border: 'none',
    background: 'transparent',
    cursor: 'pointer'
  };

  const navButtonStyle = {
    width: '40px', // 이미지 크기에 맞게 조절
    height: '40px',
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'center',
    backgroundSize: 'contain' // 이미지가 버튼 안에 꽉 차도록 설정
  };

  const prevButtonStyle = {
    ...navButtonStyle,
    backgroundImage: 'url(/images/left.png)', // 이미지 경로 설정
  };

  const nextButtonStyle = {
    ...navButtonStyle,
    backgroundImage: 'url(/images/right.png)', // 이미지 경로 설정
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'space-around', alignItems: 'center', width: '100%', padding: '10px' }}>
      <button onClick={onPrev} disabled={isPrevDisabled} style={prevButtonStyle}>
        {/* 텍스트 대신 이미지가 보이도록 내용은 비워둡니다. */}
      </button>
      <button onClick={onLike} style={likeButtonStyle}>
        ❤️
      </button>
      <button onClick={onNext} style={nextButtonStyle}>
        {/* 텍스트 대신 이미지가 보이도록 내용은 비워둡니다. */}
      </button>
    </div>
  );
};

export default VideoControls;