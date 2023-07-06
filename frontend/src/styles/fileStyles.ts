const styles:any = {
    tree: {
      base: {
        listStyle: "none",
        backgroundColor: "rgb(236, 236, 236)",
        marginTop: 8,
        padding: 0,
        paddingRight: "0px",
        color: "black",
        fontFamily:
          "Apple-System,Arial,Helvetica,PingFang SC,Hiragino Sans GB,Microsoft YaHei,STXihei,sans-serif",
        fontSize: "0.9em",
        minWidth: "fit-content",
        width: "250px",
        overflow:"auto",
        textOverflow:"ellipsis"
      },
      node: {
        base: {
          position: "relative",
          whiteSpace: "pre",
          width:"230px",
        },
        link: {
          cursor: "pointer",
          position: "relative",
          padding: "0px 5px",
          display: "block",
        
        },
        activeLink: {
          backgroundColor: "#D3D3D3",
          width: "100%",
        },
        toggle: {
          base: {
            position: "relative",
            display: "inline-block",
            verticalAlign: "top",
            marginLeft: "-5px",
            height: "18px",
            width: "24px",
          },
          wrapper: {
            position: "absolute",
            top: "50%",
            left: "50%",
            margin: "-8px 0 0 1px",
            height: "14px",
          },
          height: 6,
          width: 6,
          arrow: {
            fill: "black",
            strokeWidth: 0
          }
        },
        header: {
          base: {
            display: "inline-block",
            verticalAlign: "top",
            color: "black",
            whiteSpace: "pre",
            padding: "4px 0", 
            width:"200px",
            // overflow:"auto",
            textOverflow:"ellipsis"
          },
          connector: {
            width: "2px",
            height: "12px",
            borderLeft: "solid 2px black",
            borderBottom: "solid 2px black",
            position: "absolute",
            top: "0px",
            left: "-21px",
          },
          title: {
            lineHeight: "24px",
            verticalAlign: "middle", 
          }
        },
        subtree: {
          listStyle: "none",
          paddingLeft: "19px", 
          maxWidth:"200px",
          width:"250px",
        },
        loading: {
          color: "#E2C089"
        }
      }
    }
  };
export default styles
  