import { RefObject, useEffect } from "react";
import React from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import { Box, Typography } from "@mui/material";
import { useRef } from "react";
import Player from "video.js/dist/types/player";

export const VideoComponent = ({options, title}: {
  options:{ 
    autoplay: boolean,
    controls: boolean,
    responsive: boolean,
    fluid: boolean,
    sources: 
      {
        src: string,
        type: string,
      }[]
    ,
  }, 
  title: string
}) => {
    const videoRef:ref = useRef(null);
    const playerRef:ref = useRef(null);
  
    const handlePlayerReady = (player:Player, playerRef:ref) => {
      playerRef.current = player as unknown as HTMLElement;
    }
    useEffect(() => {
      if (!playerRef.current) {
        const videoElement = document.createElement("video-js");
        videoElement.classList.add('vjs-big-play-centered');
        videoRef.current?.appendChild(videoElement);
  
        const player:Player = playerRef.current = videojs(videoElement, options, () => {
          videojs.log('player is ready');
          handlePlayerReady && handlePlayerReady(player, playerRef);
        });
  
      } else {
        const player = playerRef.current as unknown as Player;
  
        player.autoplay(options.autoplay);
        player.src(options.sources);
      }
      }, [options, videoRef]);
  
    useEffect(() => {
      const player = playerRef.current as unknown as Player;
  
      return () => {
        if (player && !player.isDisposed()) {
          player.dispose();
          playerRef.current = null;
        }
      };
    }, [playerRef]);
  
    return (
      <Box sx={{maxWidth : "90%"}}>
        <Typography fontSize="18px" fontWeight="10px" >{title}</Typography>
        <Box data-vjs-player>
          <div ref={videoRef as RefObject<HTMLDivElement>} style={{}}/>
        </Box>
      </Box>
    );
  }
  
  export default VideoComponent;