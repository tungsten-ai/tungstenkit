// import 'tarang/dist/index.css'        //is this needed?
import { Box, Button } from "@mantine/core";
import { IconPlayerPauseFilled, IconPlayerPlayFilled } from "@tabler/icons-react";
import { useEffect, useId, useState } from "react";
import styled from "styled-components";

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
  background: #e9e9e9;
  border: 1px black;
  outline: none;
  cursor: pointer;
  padding-bottom: 3px;
  &:hover {
    background: #ddd;
  }
`;

function AudioComponent({ src }: { src: string }) {
  const id = useId();
  const [playing, setPlaying] = useState(false);
  const [waveform, setWaveform] = useState();
  let isNotcreated = true; //temporary implementation : the screen is rerendered twice for currently unknown reason, so the waveform is also loaded twice if we dont use isNotCreated flag.
  useEffect(() => {
    if (isNotcreated) {
      const initWaveSurfer = async () => {
        const WaveSurfer: { create: Function } = (await import("wavesurfer.js")).default;
        const container = document.getElementById(`waveform${id}`);
        const waveformCreated = WaveSurfer.create({
          barWidth: 3,
          barRadius: 3,
          barGap: 2,
          barMinHeight: 1,
          cursorWidth: 1,
          container: container,
          backend: "WebAudio",
          height: 80,
          progressColor: "#black",
          responsive: true,
          waveColor: "#C4C4C4",
          cursorColor: "transparent",
        });
        setWaveform(waveformCreated);
        waveformCreated.load(src);
        waveformCreated.on("finish", () => {
          setPlaying(false);
        });
      };
      initWaveSurfer();
      isNotcreated = false;
    }
  }, []);

  const handlePlay = (waveform: { playPause: Function } | undefined) => {
    setPlaying(!playing);
    if (waveform) waveform.playPause();
  };

  return (
    <Box sx={{ maxWidth: "90%" }}>
      <Box style={{ padding: "0px", margin: "0px" }}>
        <WaveformContianer style={{ padding: "0px", margin: "0px", height: "90px" }}>
          <Button
            sx={(theme) => ({ border: "none", borderRadius: theme.radius.sm, width: "120px" })}
            variant="contained"
            leftIcon={playing ? <IconPlayerPauseFilled /> : <IconPlayerPlayFilled />}
            onClick={(e) => handlePlay(waveform)}
          >
            {!playing ? "Play" : "Pause"}
          </Button>
          <Wave id={`waveform${id}`} style={{ padding: "0px", margin: "0px", height: "80px" }} />{" "}
          {/*TODO: remove 0px if unnecessary */}
          <audio id={`track${id}`} src={src} style={{ padding: "0px", margin: "0px" }} />
        </WaveformContianer>
      </Box>
    </Box>
  );
}

export default AudioComponent;
