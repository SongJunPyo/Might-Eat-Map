// // src/App.js
 
import React, { useState, useEffect, useCallback, useRef } from 'react';
import Map from './Map';
import { BottomSheet } from 'react-spring-bottom-sheet';
import 'react-spring-bottom-sheet/dist/style.css';
import YouTubePlayer from './YouTubePlayer';
import VideoControls from './VideoControls';
import PlaceDetails from './PlaceDetails';
import './App.css';
 

// 두 지점 간의 거리를 km 단위로 계산하는 함수 (Haversine formula)
const getDistance = (lat1, lon1, lat2, lon2) => {
  if ((lat1 === lat2) && (lon1 === lon2)) {
    return 0;
  }
  const radlat1 = Math.PI * lat1 / 180;
  const radlat2 = Math.PI * lat2 / 180;
  const theta = lon1 - lon2;
  const radtheta = Math.PI * theta / 180;
  let dist = Math.sin(radlat1) * Math.sin(radlat2) + Math.cos(radlat1) * Math.cos(radlat2) * Math.cos(radtheta);
  if (dist > 1) {
    dist = 1;
  }
  dist = Math.acos(dist);
  dist = dist * 180 / Math.PI;
  dist = dist * 60 * 1.1515 * 1.609344;
  return dist;
}
 
const timeStringToSeconds = (timeString) => {
  if (!timeString || typeof timeString !== 'string' || !timeString.includes(':')) {
    return 0;
  }
  // 'HH:MM:SS'를 ':' 기준으로 나누어 배열로 만듭니다. (예: ["00", "07", "56"])
  const parts = timeString.split(':');
 
  // 각 부분을 정수로 변환합니다.
  const hours = parseInt(parts[0], 10);
  const minutes = parseInt(parts[1], 10);
  const seconds = parseInt(parts[2], 10);
 
  // 총 초를 계산하여 반환합니다.
  return (hours * 3600) + (minutes * 60) + seconds;
};
 
const transformGemData = (gem, index) => ({ // map의 두 번째 인자인 index를 받습니다.
  id: `${gem.video_id}-${index}`, // 예: 'Abcde-0', 'Abcde-1'
  place_name: gem.gem_name,
  gem_type: gem.gem_type,
  y: gem.latitude,
  x: gem.longitude,
  recommend_reason: gem.recommend_reason,
  address: gem.address,
  category: gem.category,
  videoId: gem.video_id,
  startTime: timeStringToSeconds(gem.start_timestamp || '00:00:00'),
  final_score: gem.final_score,
});
 
function App() {
  // 백엔드에서 받아온 데이터를 저장할 state
  const [allPlaces, setAllPlaces] = useState([]);
  const [searchedPlaces, setSearchedPlaces] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearchActive, setIsSearchActive] = useState(false);
  const [mapCenter, setMapCenter] = useState({ y:35.16483256337843, x:129.13824960664704 });
  const [focusedPlace, setFocusedPlace] = useState(null);
  const [currentVideo, setCurrentVideo] = useState(null);
  const [history, setHistory] = useState([]);
  const [likedPlaces, setLikedPlaces] = useState(new Set());
  const focusedPlaceRef = useRef(focusedPlace);
  const allPlacesRef = useRef(allPlaces);
  const [referencePoint, setReferencePoint] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isVideoVisible, setIsVideoVisible] = useState(true);
  const [isFirstLoad, setIsFirstLoad] = useState(true); // 첫 로드 여부 추적
 
  // ✅ 1. 슬라이더 값 관리를 위한 state 추가 (각 항목 1-10, 기본값 5)
  const [weights, setWeights] = useState({
    view_count: 5,
    comment_score: 5,
    script_score: 5,
    engagement_ratio: 5,
    like_ratio: 5,
    sub_view_ratio: 5,
  });
 
    // ✅ 1. 컴포넌트가 처음 마운트될 때 백엔드에서 데이터를 가져옵니다.
  useEffect(() => {
    const fetchPlaces = async () => {
      const totalWeight = Object.values(weights).reduce((sum, val) => sum + val, 0);

      // totalWeight가 0이면 API 호출을 건너뜁니다 (오류 방지)
      if (totalWeight === 0) {
        setAllPlaces([]); // 목록을 비웁니다.
        return;
      }

      const scores = {
        view_count_weight : weights.view_count / totalWeight,
        comment_score_weight : weights.comment_score / totalWeight,
        script_score_weight : weights.script_score / totalWeight,
        engagement_ratio_weight : weights.engagement_ratio / totalWeight,
        like_ratio_weight : weights.like_ratio / totalWeight,
        sub_view_ratio_weight : weights.sub_view_ratio / totalWeight
      };

      const queryString = new URLSearchParams(scores).toString();

      try {
        const response = await fetch(`http://localhost:9000/react_web/get_all_gem?${queryString}`);
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        const data = await response.json();
       
        // ✅ 2. 백엔드 데이터를 프론트엔드 형식에 맞게 변환합니다.
        const transformedData = data.map(transformGemData);
        setAllPlaces(transformedData);

        // 첫 로드일 때만 초기 설정을 진행합니다.
        if (isFirstLoad) {
          const initialCenter = { lat: 35.16483256337843, lng: 129.13824960664704 };
          const placesWithDistance = transformedData.map(place => ({
            ...place,
            distance: getDistance(initialCenter.lat, initialCenter.lng, place.y, place.x)
          }));
          placesWithDistance.sort((a, b) => a.distance - b.distance);

          setSearchedPlaces(placesWithDistance); // 정렬된 목록을 searchedPlaces에 저장
          setIsSearchActive(true); // 검색 활성 상태로 만들어 사이드바에 거리순 목록 표시
          setReferencePoint({ y: initialCenter.lat, x: initialCenter.lng }); // 마커 표시를 위한 기준점 설정
         
          // 최초 로드 시 첫번째 장소 포커스
          if (placesWithDistance.length > 0) {
              handlePlaceSelect(placesWithDistance[0]);
          }
          
          setIsFirstLoad(false); // 첫 로드 완료 표시
        } else {
          // 첫 로드가 아닌 경우 (우선순위 비율 변경 등)
          // 현재 기준점이 있다면 그 기준점을 기준으로 다시 정렬
          const currentReferencePoint = referencePoint;
          const currentFocusedPlace = focusedPlace;
          
          if (currentReferencePoint) {
            const placesWithDistance = transformedData.map(place => ({
              ...place,
              distance: getDistance(currentReferencePoint.y, currentReferencePoint.x, place.y, place.x)
            }));
            placesWithDistance.sort((a, b) => a.distance - b.distance);
            setSearchedPlaces(placesWithDistance);
            
            // 기존에 포커스된 장소가 있다면 새로운 데이터에서 해당 장소를 찾아서 유지
            if (currentFocusedPlace) {
              const updatedFocusedPlace = placesWithDistance.find(p => p.id === currentFocusedPlace.id);
              if (updatedFocusedPlace) {
                setFocusedPlace(updatedFocusedPlace);
              }
            }
          } else {
            // 기준점이 없다면 전체 목록만 업데이트
            setSearchedPlaces(transformedData);
          }
        }

      } catch (error) {
        console.error("Failed to fetch places:", error);
        // 에러 발생 시 사용자에게 알림을 주거나, 빈 배열을 유지할 수 있습니다.
      }
    };

    fetchPlaces();
  }, [weights, isFirstLoad]); // isFirstLoad 의존성 추가
 
  useEffect(() => {
    focusedPlaceRef.current = focusedPlace;
  }, [focusedPlace]);

  useEffect(() => {
    allPlacesRef.current = allPlaces;
  }, [allPlaces]);
 
  const handleSearch = async () => {
    if (!searchTerm.trim()) {
      setSearchedPlaces([]);
      setIsSearchActive(false);
      setReferencePoint(null);
      return;
    }
 
    setReferencePoint(null);
 
    try {
      // 1. 맛집 목록과 지역 좌표를 동시에 요청
      const [searchResponse, geoResponse] = await Promise.all([
        fetch(`http://localhost:9000/react_web/search_gem?query=${searchTerm}`),
        fetch(`http://localhost:9000/react_web/geocode?query=${searchTerm}`)
      ]);
 
      if (!searchResponse.ok) throw new Error('맛집 목록 검색에 실패했습니다.');
 
      const searchData = await searchResponse.json();
      let transformedData = searchData.map(transformGemData);
 
            // 2. 검색 결과가 있을 경우
      if (transformedData.length > 0 && geoResponse.ok) {
        const centerPoint = await geoResponse.json();
        setMapCenter({ y: centerPoint.lat, x: centerPoint.lng });
        setReferencePoint({ y: centerPoint.lat, x: centerPoint.lng }); // 검색 위치에 마커 표시

        transformedData.forEach(place => {
          place.distance = getDistance(centerPoint.lat, centerPoint.lng, place.y, place.x);
        });

        transformedData.sort((a, b) => a.distance - b.distance);
       
        setSearchedPlaces(transformedData);
        setIsSearchActive(true);

        // ★★★ 수정: 정렬된 목록의 첫 번째 장소를 바로 '선택'합니다. ★★★
        // 이 함수가 setFocusedPlace와 setCurrentVideo를 모두 처리합니다.
        handlePlaceSelect(transformedData[0]);
 
      } else if (transformedData.length === 0 && geoResponse.ok) {
        const centerPoint = await geoResponse.json();
       
        // 지도의 중심을 검색한 지역으로 이동
        setMapCenter({ y: centerPoint.lat, x: centerPoint.lng });
        setReferencePoint({ y: centerPoint.lat, x: centerPoint.lng });
 
        // 기존의 'allPlaces' 목록을 가져와서 거리순으로 정렬
        const placesWithDistance = allPlaces.map(place => ({
          ...place,
          distance: getDistance(centerPoint.lat, centerPoint.lng, place.y, place.x)
        }));
        placesWithDistance.sort((a, b) => a.distance - b.distance);
 
        // 정렬된 목록을 사이드바에 표시
        setSearchedPlaces(placesWithDistance);
        setIsSearchActive(true);
 
        // allPlaces가 비어있을 경우를 대비해, 목록에 아이템이 있는지 확인합니다.
        if (placesWithDistance.length > 0) {
          handlePlaceSelect(placesWithDistance[0]);
        } else {
          setFocusedPlace(null);
          setCurrentVideo(null);
        }
 
      // 3. 검색 결과와 지역 좌표 모두 없는 경우
      } else {
        // 3. 검색 결과가 없을 경우 UI 초기화
        setSearchedPlaces([]);
        setIsSearchActive(true); // "검색 결과 없음"을 표시하기 위함
        setFocusedPlace(null);
        setCurrentVideo(null);
      }
 
    } catch (error) {
      console.error("Search failed:", error);
      setSearchedPlaces([]);
    }
  };
 
    const handleMapRightClick = useCallback((location) => {
    console.log('우클릭 위치:', location); // 디버깅용 로그
    setReferencePoint(location); // 기준점 설정으로 마커 표시

    const placesWithDistance = allPlacesRef.current.map(place => ({
      ...place,
      distance: getDistance(location.y, location.x, place.y, place.x)
    }));
    placesWithDistance.sort((a, b) => a.distance - b.distance);

    setSearchedPlaces(placesWithDistance);
    setIsSearchActive(true);
  }, []); // 의존성 배열을 비워서 함수가 재생성되지 않도록 함
 
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };
 
  const handlePlaceSelect = useCallback((place) => {
 
    const prevPlace = focusedPlaceRef.current;
    // 디버깅 로그
    console.log('--- 마커 클릭 디버그 (useRef 방식) ---');
    if (prevPlace) {
      console.log(`[이전] ${prevPlace.place_name}`, { lat: prevPlace.y, lng: prevPlace.x });
    } else {
      console.log('[이전] 선택된 마커 없음');
    }
    console.log(`[현재] ${place.place_name}`, { lat: place.y, lng: place.x });
    console.log('----------------------');
 
    // 이전 장소(focusedPlace)가 있고, 새로 선택한 장소와 다를 경우에만 history에 추가
    if (focusedPlace && focusedPlace.id !== place.id) {
      setHistory(prev => [...prev, focusedPlace]);
    }
 
    // 새로운 장소로 state 업데이트
    setFocusedPlace(place);
    if (place.videoId) {
      setCurrentVideo({ id: place.videoId, start: place.startTime });
    } else {
      setCurrentVideo(null);
    }
 
    setIsVideoVisible(true);
   
  }, [focusedPlace]);
 
  const handleNextClick = () => {
    // ★★★ 1. 현재 화면에 표시된 목록(전체 또는 검색 결과)을 가져옵니다. ★★★
    const currentList = placesToShow;
 
    // 히스토리에 현재까지 본 장소의 ID를 기록합니다.
    const viewedIds = new Set(history.map(p => p.id));
    if (focusedPlace) {
      viewedIds.add(focusedPlace.id);
    }
 
    // ★★★ 2. 전체 목록(allPlaces) 대신 현재 목록(currentList)에서 다음 영상을 찾습니다. ★★★
    const potentialNextPlaces = currentList.filter(p => p.videoId && !viewedIds.has(p.id));
 
    if (potentialNextPlaces.length > 0) {
      // 다음 영상을 랜덤으로 선택합니다.
      const randomIndex = Math.floor(Math.random() * potentialNextPlaces.length);
      handlePlaceSelect(potentialNextPlaces[randomIndex]);
    } else {
      // ★★★ 3. 검색 상태에 따라 다른 알림 메시지를 보여줍니다. ★★★
      const alertMessage = isSearchActive ? "검색된 모든 영상을 다 보셨습니다!" : "모든 영상을 다 보셨습니다!";
      alert(alertMessage);
    }
  };
 
  const handlePrevClick = () => {
    if (history.length === 0) return;
    const lastPlace = history[history.length - 1];
    setHistory(prev => prev.slice(0, -1));
    
    // handlePlaceSelect 대신 직접 state 업데이트 (무한루프 방지)
    setFocusedPlace(lastPlace);
    if (lastPlace.videoId) {
      setCurrentVideo({ id: lastPlace.videoId, start: lastPlace.startTime });
    } else {
      setCurrentVideo(null);
    }
    setIsVideoVisible(true);
  };
 
  const handleLikeClick = () => {
    if (!focusedPlace) return;
    setLikedPlaces(prev => {
      const newLiked = new Set(prev);
      if (newLiked.has(focusedPlace.id)) {
        newLiked.delete(focusedPlace.id);
      } else {
        newLiked.add(focusedPlace.id);
      }
      return newLiked;
    });
  };
 
 
  const handleSetCurrentLocation = () => {
    if (!navigator.geolocation) {
      alert('이 브라우저에서는 위치 정보 기능을 사용할 수 없습니다.');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        const currentLocation = { y: latitude, x: longitude };

        console.log('📍 현재 내 위치 좌표:', { latitude, longitude });

        setReferencePoint(currentLocation);
        setMapCenter(currentLocation);
        setIsSearchActive(true);

        if (allPlacesRef.current.length > 0) {
          const placesWithDistance = allPlacesRef.current.map((place) => ({
            ...place,
            distance: getDistance(currentLocation.y, currentLocation.x, place.y, place.x),
          }));

          placesWithDistance.sort((a, b) => a.distance - b.distance);
          setSearchedPlaces(placesWithDistance);
        } else {
          setSearchedPlaces([]);
        }

        alert('현재 위치 기준으로 지도를 이동하고 장소 목록을 정렬했습니다.');
      },
      (error) => {
        console.error('Geolocation error: ', error);
        alert('현재 위치를 가져올 수 없습니다. 브라우저의 위치 정보 접근 권한을 확인해주세요.');
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };
 
  // ✅ 3. 하드코딩된 allRestaurants 대신 allPlaces state를 사용합니다.
  const placesToShow = isSearchActive ? searchedPlaces : allPlaces;
  const isLiked = focusedPlace ? likedPlaces.has(focusedPlace.id) : false;
 
 
  // ✅ 2. 슬라이더 값이 변경될 때 state를 업데이트하는 함수
  const handleWeightChange = (e) => {
    const { name, value } = e.target;
    const numericValue = Number(value); // 변경될 값 (숫자)
 
    // 1. 만약 이 변경으로 모든 값이 0이 되는지 미리 확인합니다.
    const tempWeights = { ...weights, [name]: numericValue };
    const totalWeight = Object.values(tempWeights).reduce((sum, val) => sum + val, 0);
 
    // 2. 만약 총합이 0이라면, 경고를 표시하고 함수 실행을 중단합니다.
    if (totalWeight === 0) {
      alert("적어도 하나의 가중치는 0보다 커야 합니다.");
      return; // 여기서 함수가 종료되어 setWeights가 호출되지 않습니다.
    }
 
    // 3. 총합이 0이 아닐 경우에만 state를 정상적으로 업데이트합니다.
    setWeights(prevWeights => ({
      ...prevWeights,
      [name]: numericValue,
    }));
  };
 
  // ✅ 3. 렌더링할 메트릭 목록 (코드를 깔끔하게 만들기 위함)
  const metrics = [
    { key: 'view_count', label: '조회수' },
    { key: 'comment_score', label: '댓글 긍정도' },
    { key: 'script_score', label: '크리에이터 긍정도' },
    // { key: 'engagement_ratio', label: '조회수 대비 댓글 수' },
    { key: 'like_ratio', label: '조회수 대비 좋아요 수' },
    { key: 'sub_view_ratio', label: '채널신뢰도' },
  ];
 
  return (
    <div className="App">
      <button className="mobile-menu-button" onClick={() => setIsSidebarOpen(true)}>
        ☰
      </button>
     
      <main className="main-content">
        <div className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
          <button className="mobile-close-button" onClick={() => setIsSidebarOpen(false)}>
            &times;
          </button>
 
          <div className="App-header">
            <img src="/images/web_title.png" alt="창원 먹을지도" style={{ height: '100px' }} />
          </div>
          <div className="search-box">
            <input
              type="text"
              placeholder="상호명 또는 카테고리 검색"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                if (!e.target.value.trim()) {
                  setIsSearchActive(false);
                  setReferencePoint(null); // 입력창 클리어 시 초기화
                }
              }}
              onKeyDown={handleKeyPress}
            />
            <button onClick={handleSearch}>🔍</button>
          </div>
          {/* ✅ 2. 현재 위치 버튼 추가 */}
          <div style={{ padding: '10px 15px', borderBottom: '1px solid #eee' }}>
            <button
              onClick={handleSetCurrentLocation}
              style={{
                width: '100%',
                padding: '12px',
                backgroundColor: '#28a745', // 초록색 배경
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer',
                fontSize: '1em',
                fontWeight: 'bold',
              }}
            >
              📍 내 위치로 이동
            </button>
          </div>
          <ul className="place-list">
            {placesToShow.length > 0 ? (
              placesToShow.map((place) => (
                <li key={place.id} className="place-item" onClick={() => handlePlaceSelect(place)}>
                  <h4>{place.place_name}</h4>
                  {/* ✅ 5. isSearchActive와 place.distance가 있을 때만 거리 표시 */}
                  {isSearchActive && place.distance !== undefined && (
                    <p className="details-distance">
                      🚩 기준점으로부터 {place.distance.toFixed(2)} km
                    </p>
                  )}
                  <p className="details-category">🏷️ {place.category}</p>
                  <p className="details-address">📍 {place.address}</p>
                </li>
              ))
            ) : (
              <div className="empty-list">데이터를 불러오는 중이거나, 검색 결과가 없습니다.</div>
            )}
          </ul>
        </div>
 
        <div className="map-container">
          <Map
            places={placesToShow}
            focusedPlace={focusedPlace}
            mapCenter={mapCenter}
            onMarkerClick={handlePlaceSelect}
            onMapRightClick={handleMapRightClick}
            referencePoint={referencePoint}
          />
        </div>
 
        {isVideoVisible && (
          <div className="video-container">
            {/* ✅ 3. 비디오 컨테이너를 닫는 X 버튼 추가 */}
            <button
              className="close-video-button"
              onClick={() => setIsVideoVisible(false)}
              aria-label="영상 닫기"
            >
              닫기
            </button>
 
            {currentVideo ? (
              <>
                <YouTubePlayer
                  key={`${currentVideo.id}-${currentVideo.start}`}
                  video={currentVideo}
                />
                <PlaceDetails place={focusedPlace} />
                <VideoControls
                  onPrev={handlePrevClick}
                  onNext={handleNextClick}
                  onLike={handleLikeClick}
                  isLiked={isLiked}
                  isPrevDisabled={history.length === 0}
                />
              </>
            ) : (
              <div className="video-placeholder">
                <p>마커를 클릭하면 관련 영상이 재생됩니다.</p>
              </div>
            )}
          </div>
        )}
 
 
        {/* ✅ 여기에 새로운 컨테이너 추가 */}
        <div className="top-right-container">
          <h3> ⚙️ 우선순위 비율 </h3>
          {metrics.map(metric => (
            <div className="slider-group" key={metric.key}>
              <label htmlFor={metric.key}>{metric.label}</label>
              <div className="slider-wrapper">
                <input
                  type="range"
                  id={metric.key}
                  name={metric.key}
                  min="0"
                  max="10"
                  value={weights[metric.key]}
                  onChange={handleWeightChange}
                  className="weight-slider"
                />
                <span className="slider-value">{weights[metric.key]}</span>
              </div>
            </div>
          ))}
        </div>
 
      </main>
    </div>
  );
}
 
 
 
export default App;