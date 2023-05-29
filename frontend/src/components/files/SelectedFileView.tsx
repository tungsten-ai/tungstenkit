import React from 'react'

function SelectedFileView({file}:{file:File}) {
  if(file.name){
    const fileNameArray = file.name.split("/")
    const actualFileName = fileNameArray[fileNameArray.length-1]
    if( actualFileName.includes("png")||actualFileName.includes("jpg")||actualFileName.includes("jpeg")){
      return (
        <img key={1} src={file.content} style={{width:"100%", border:"0px solid #d3d3d3"}}></img>
      )
    }
  }

  return (
    <pre className="line-numbers" style={{height:"100%", width:"100%",  marginTop:"0px"}}>
        <code className="language-">{file.content}</code>  {/*"can add classname= from prismjs here"*/}
    </pre>
  )
}

export default SelectedFileView