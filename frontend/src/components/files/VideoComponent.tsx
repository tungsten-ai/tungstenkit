import { Box, Flex } from "@mantine/core";
import { RefObject, useEffect, useRef } from "react";
import videojs from "video.js";
import Player from "video.js/dist/types/player";
import "video.js/dist/video-js.css";

function VideoComponent({
  src,
  mimeType,
  autoplay = false,
  controls = true,
  responsive = true,
  fluid = true,
}: {
  src: string;
  mimeType: string;
  autoplay?: boolean;
  controls?: boolean;
  responsive?: boolean;
  fluid?: boolean;
}) {
  const videoRef = useRef<HTMLElement | null>(null);
  const playerRef = useRef<HTMLElement | null>(null);
  const handlePlayerReady = (player: Player, playerRef: HTMLElement) => {
    playerRef.current = player;
  };
  useEffect(() => {
    const options = {
      autoplay,
      controls,
      responsive,
      fluid,
      sources: [
        {
          src,
          type: mimeType,
        },
      ],
    };
    if (!playerRef.current) {
      const videoElement = document.createElement("video-js");
      videoElement.classList.add("vjs-big-play-centered");
      videoRef.current?.appendChild(videoElement);

      const player: Player = (playerRef.current = videojs(videoElement, options, () => {
        handlePlayerReady && handlePlayerReady(player, playerRef);
      }));
    } else {
      const player = playerRef.current as unknown as Player;

      player.autoplay(options.autoplay);
      player.src(options.sources);
    }
  }, [src, mimeType, autoplay, controls, responsive, fluid, videoRef]);

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
    <Flex direction="column" sx={{ maxWidth: "100%", gap: "0.4rem" }}>
      <Box data-vjs-player>
        <div ref={videoRef as RefObject<HTMLDivElement>} style={{}} />
      </Box>
    </Flex>
  );
}

export default VideoComponent;
