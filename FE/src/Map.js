// src/Map.js

import React, { useEffect, useRef, useState } from 'react';

const { kakao } = window;

const Map = ({ places, focusedPlace, mapCenter, onMarkerClick, onMapRightClick, referencePoint  }) => {
  const mapRef = useRef(null);
  const mapContainerRef = useRef(null);      // ✅ 지도 div DOM 참조용 ← 여기에 추가
  const overlaysRef = useRef({});
  const [isMapLoaded, setIsMapLoaded] = useState(false);
  const [selectionMarker, setSelectionMarker] = useState(null);

  // 1. 지도 초기화 로직: 컴포넌트가 처음 마운트될 때 한 번만 실행됩니다.
  useEffect(() => {
    if (!mapRef.current) {
      kakao.maps.load(() => {
        const map = new kakao.maps.Map(mapContainerRef.current, {
          center: new kakao.maps.LatLng(35.16483256337843, 129.13824960664704),
          level: 4,
          scrollwheel: true
        });
        mapRef.current = map;
        setIsMapLoaded(true);

       
      });
    }
//     kakao.maps.load(() => {
//       const mapContainer = document.getElementById('map');
//       const mapOption = {
//         center: new kakao.maps.LatLng(35.16483256337843, 129.13824960664704),
//         level: 4,
//         scrollwheel: true 
//       };
//       const map = new kakao.maps.Map(mapContainer, mapOption);
//       mapRef.current = map;
//       setIsMapLoaded(true); // 지도가 로드되었음을 state에 알립니다.
//     });
  }, []); // 의존성 배열이 비어 있으므로 한 번만 실행됩니다.

  // 2. 우클릭 이벤트 리스너 관리 로직: 지도가 로드되거나, onMapRightClick 함수가 변경될 때마다 실행됩니다.
  useEffect(() => {
    // 지도가 아직 로드되지 않았다면 아무것도 하지 않습니다.
    if (!isMapLoaded) return;

    const map = mapRef.current;

    // 이벤트 리스너로 사용할 함수입니다.
    const listener = (mouseEvent) => {
      const latlng = mouseEvent.latLng;
      onMapRightClick({ y: latlng.getLat(), x: latlng.getLng() });
    };

    // 지도에 'rightclick' 이벤트 리스너를 등록합니다.
    kakao.maps.event.addListener(map, 'rightclick', listener);

    // useEffect의 cleanup 함수: 컴포넌트가 언마운트되거나, 의존성이 변경되어 이 effect가 다시 실행되기 전에 호출됩니다.
    return () => {
      // 이전에 등록했던 리스너를 제거합니다. (메모리 누수 방지)
      kakao.maps.event.removeListener(map, 'rightclick', listener);
    };
  }, [isMapLoaded, onMapRightClick]); // onMapRightClick 함수가 새로워질 때마다 리스너를 교체합니다.

  // 장소 오버레이 관리 (기존 코드와 동일)
  useEffect(() => {
    if (!isMapLoaded || !mapRef.current) return;
    const map = mapRef.current;
    Object.values(overlaysRef.current).forEach(overlay => overlay.setMap(null));
    overlaysRef.current = {};
    if (places && places.length > 0) {
      places.forEach(place => {

        const displayCategory = place.category 
            ? place.category.split(',').slice(0, 1).join(', ') 
            : '';

        const content = `
          <div class="custom-overlay">
            <div class="icon">🍜</div>
            <div class="text">
              <div class="title">${place.place_name}</div>
              <div class="category">${displayCategory}</div>
            </div>
          </div>
        `;
        const position = new kakao.maps.LatLng(place.y, place.x);
        const customOverlay = new kakao.maps.CustomOverlay({
          position, content, yAnchor: 1.4
        });
        customOverlay.a.onclick = () => onMarkerClick(place);
        customOverlay.setMap(map);
        overlaysRef.current[place.id] = customOverlay;
      });
    }
  }, [places, isMapLoaded, onMarkerClick]);

  // 선택된 장소 강조 효과 (기존 코드와 동일)
  useEffect(() => {
    if (!mapRef.current) return;
    Object.values(overlaysRef.current).forEach(o => o.setZIndex(0));
    document.querySelectorAll('.custom-overlay.focused').forEach(el => {
      el.classList.remove('focused');
    });
    if (focusedPlace) {
      const overlay = overlaysRef.current[focusedPlace.id];
      if (overlay) {
        overlay.setZIndex(10);
        mapRef.current.panTo(overlay.getPosition());
        const overlayElement = overlay.a.querySelector('.custom-overlay');
        if (overlayElement) {
          overlayElement.classList.add('focused');
        }
      }
    }
  }, [focusedPlace]);
  
  // 지도 중심 이동 (기존 코드와 동일)
  useEffect(() => {
    if (!mapRef.current || !mapCenter) return;
    const map = mapRef.current;
    const newCenter = new kakao.maps.LatLng(mapCenter.y, mapCenter.x);
    map.panTo(newCenter);
    if (mapCenter.level && map.getLevel() !== mapCenter.level) {
      map.setLevel(mapCenter.level);
    }
  }, [mapCenter]);

  // 우클릭 마커 관리 (기존 코드와 동일)
  useEffect(() => {
    if (!isMapLoaded) return;
    if (selectionMarker) {
      selectionMarker.setMap(null);
    }
    if (referencePoint ) {
      const marker = new kakao.maps.Marker({
        position: new kakao.maps.LatLng(referencePoint .y, referencePoint .x),
      });
      marker.setMap(mapRef.current);
      setSelectionMarker(marker);
    } else {
      setSelectionMarker(null);
    }
  }, [referencePoint , isMapLoaded]);



  return (
    <div id="map"  ref={mapContainerRef} tabIndex={0} style={{ width: '100%', height: '100%', outline: 'none' }}></div>
  );
};

export default Map;