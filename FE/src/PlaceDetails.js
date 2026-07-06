// src/PlaceDetails.js

import React from 'react';

const PlaceDetails = ({ place }) => {
  // 선택된 장소가 없으면 아무것도 표시하지 않음
  if (!place) {
    return null;
  }

  return (
    <div className="place-details-container">
      <h3>{place.place_name}</h3>
      <p className="details-final_score">🏆 {place.final_score}</p>
      <p className="details-category">🏷️ {place.category}</p>
      <p className="details-address">📍 {place.address}</p>
      <p className="details-recommend_reason">💁‍♂️ {place.recommend_reason}</p>
    </div>
  );
};

export default PlaceDetails;