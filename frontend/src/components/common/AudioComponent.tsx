import React, { useEffect, useState } from 'react'
import styled from "styled-components";
import { Box, Button, Typography } from '@mui/material';
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline';
import PauseCircleOutlineIcon from '@mui/icons-material/PauseCircleOutline';

export const WaveformContianer = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  height: 100px;
  width: 100%;
  background: transparent;
  gap: 2rem;
`;

export const Wave = styled.div`
  width: 100%;
  height: 90px;
`;

export const PlayButton = styled.button`
  display: flex;
  justify-content: center;
  align-items: center;
  width: 60px;
  height: 60px;
  background: #E9E9E9;
  border: 1px black;
  outline: none;
  cursor: pointer;
  padding-bottom: 3px;
  &:hover {
    background: #ddd;
  }
`;

function AudioComponent({url, title, audioId}:{url:string, title:string, audioId:string|number}) {
  const [playing, setPlaying] = useState(false)
  const [waveform, setWaveform]= useState<{playPause: Function}>()
  let isNotcreated = true    //temporary implementation : the screen is rerendered twice for currently unknown reason, so the waveform is also loaded twice if we dont use isNotCreated flag.
  
  useEffect(()=>{
    if (isNotcreated){
      const initWaveSurfer = async ()=>{
        const waveContainer = document.getElementById(`waveform${audioId}`)
        const WaveSurfer:{create : Function} = (await import( "wavesurfer.js")).default

        const waveformCreated = WaveSurfer.create({
          barWidth: 3,
          barRadius: 3,
          barGap: 2,
          barMinHeight: 1,
          cursorWidth: 1,
          container: waveContainer,
          backend: "WebAudio",
          height: 80,
          progressColor: "#black",
          responsive: true,
          waveColor: "#C4C4C4",
          cursorColor: "transparent"
        })
        setWaveform (waveformCreated)
        waveformCreated.load(url);
        waveformCreated.on("finish", ()=>{setPlaying(false)})
      }
      initWaveSurfer()
      isNotcreated = false
    }
  }, [])

  const handlePlay = (waveform:{playPause:Function}|undefined) => {
    setPlaying(!playing)
    if ( waveform) waveform.playPause();
  };

  return (
  <Box sx={{maxWidth:"90%"}}>
    <Typography fontSize="18px" fontWeight="10px" sx={{marginBottom:"-20px"}} >{title}</Typography>
    <Box style={{padding:'0px', margin:"0px"}}>
        <WaveformContianer style={{padding:'0px', margin:"0px", height:"90px"}}>
          <Button
              sx={{border:"none", borderRadius:"3px", width:"120px" }}
              variant="contained"
              startIcon={playing?<PauseCircleOutlineIcon/> : <PlayCircleOutlineIcon />}
              onClick={(e)=>handlePlay(waveform)}
            >
            {!playing ? "Play" : "Pause"}
          </Button>
          <Wave id={`waveform${audioId}`} style={{padding:'0px', margin:"0px", height:"80px"}} />  {/*TODO: remove 0px if unnecessary */}
          <audio id={`track${audioId}`} src={url} style={{padding:'0px', margin:"0px"}} />
        </WaveformContianer>
      </Box>
    </Box>
  )
}

export default AudioComponent


