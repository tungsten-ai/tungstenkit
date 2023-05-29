import React from "react";
import { Treebeard, decorators } from "react-treebeard-ts";
import { useState } from "react";
import styles from "./styles";
import Prism from "prismjs";
import "prismjs/themes/prism.css";
import { useEffect } from "react";
import { Box, Button, Divider, Typography } from "@mui/material";
// import 'prism-themes/themes/prism-one-light.css';
import 'prismjs/plugins/line-numbers/prism-line-numbers.js'
import 'prismjs/plugins/line-numbers/prism-line-numbers.css'
import { getClientSideAxios } from "@/axios";
import getModelAPI from "@/api/model";
import FolderIcon from '@mui/icons-material/Folder';
import ArticleOutlinedIcon from '@mui/icons-material/ArticleOutlined';
import InitialView from "./InitialView";
import DownloadBtn from "./DownloadBtn";
import SelectedFileView from "./SelectedFileView";

export default function FilesView({model}:{model:model}){
    const axiosInstance = getClientSideAxios()  
    const modelAPI = getModelAPI(axiosInstance)

    const projectSlug = model.project_slug
    const namespaceSlug = model.namespace_slug 
    const modelVersion = model.version

    const [fileTree, setFileTree]:[fileTree:any, setFileTree:any] = useState({})
    const [file, setFileContent]:[file:any, setFileContent:any] = useState()
    const [cursor, setCursor] =useState({active:false})
    
    const onToggle = async (node:any, toggled:any) => {
      if (cursor) {
        cursor.active = false;
      }
      // if(toggled){          //TODO: check if these conditions are unnecessary, remove if yes
      // }
      // else{
      // }
      if (node.children) {
        node.toggled = toggled;
      }
      setCursor(node);
      setFileTree(Object.assign({}, fileTree));
      

      if (node.type=='file'){ 
        const fileName = node.name
        if(fileName.includes("png")||fileName.includes("jpeg")||fileName.includes("jpg")){
          visualizeImage(node)
        }       
        else {let fileContentFetched = (await modelAPI.getFile(node.totalPath.split("path=")[1])).data  //temp solution to bypass react error 
        
        if (typeof fileContentFetched !="string"){
          fileContentFetched = JSON.stringify(fileContentFetched)
        } 
        setFileContent({content:fileContentFetched, name:node.name})}      
      }
    };

    const visualizeImage=async (node:any)=>{
      const img = (await modelAPI.getFile(`${node.name}`, {responseType:"arraybuffer"})).data  //TODO: test
      const imgType=node.name.split(".")[1]
      const imageBlob = new Blob([img], {
        type: `image/${imgType}`
      })
      const imageObjectURL = URL.createObjectURL(imageBlob);
      setFileContent({content:imageObjectURL, name:node.name})
    }   

    const downloadAllZip =async ()=>{
      const zipFileOfModel =(await modelAPI.getModelZipFile(projectSlug, namespaceSlug, modelVersion, {responseType:"blob"})).catch().data
      const link = document.createElement('a');
      const urlForDownload = URL.createObjectURL(zipFileOfModel);
      link.href = urlForDownload;
      link.download = 'archive.zip';
      link.click();   //TODO: check if it is needed to remove the created link element
    }
    
    const loadFileTree = async()=>{
      const tree = (await modelAPI.getModelTree(projectSlug, namespaceSlug, modelVersion)).data
      const queryForSearch = `/projects/${namespaceSlug}/${projectSlug}/models/${modelVersion}/tree?path=`
      const retrieveFulltree = async(treSubArray:any, treeQuery:any)=>{
        treSubArray.forEach(async (dir:any)=>{
          dir.totalPath = `${treeQuery+"/"+dir.name}`
          if(dir.type=="folder"){
            const { data } = await axiosInstance.get(`${treeQuery+"/"+dir.name}`);
            dir.children = data
            retrieveFulltree(dir.children,`${treeQuery+"/"+dir.name}`)
          }
        })
      }
      retrieveFulltree(tree, queryForSearch)
      const fileTreeTest = {  
        name:"files",
        children: tree}
      setFileTree(fileTreeTest)
    }

    useEffect(() => { 
      // loadFileTree() 
    }, []);


    useEffect(()=>{   //Above effect must be done only once, this effect must be done at every re-render
      Prism.highlightAll()
    })

    const fileView = file?<SelectedFileView file={file}/>:<InitialView/>
    return (
    <Box>
    <Box >
        <Box sx={{display:"flex"}}>
          <Box id="treeView" sx={{display:"inline"}}>
            <DownloadBtn onClick={downloadAllZip}/>
            <Divider sx={{ my:"10px", width:"120%", float:"left",color:"black" }} />
            
            <Box className="table-struct" sx={{ mx:"20%"}}>
              <Treebeard
                data={fileTree}
                onToggle={onToggle}
                style={styles}
                decorators={{ ...decorators, Header:CustomHeader }}
              />
            </Box>
          </Box>
          <Box id="fileContentContainer" sx={{display:"inline", maxHeight: "100%", minHeight:"25vw", width:"85%", border:"1px solid #D3D3D3",marginLeft:"5%", marginTop:"8px"}}>
            {fileView}
          </Box>
        </Box>  
        <Box> 
        </Box>
      </Box>
      </Box>
    );
  }

const CustomHeader =  ({ node, style }:{ node:any, style:any}) => {
  const folderIcon = <FolderIcon sx={{fontSize:"16px", marginTop:"4px", marginRight:"5px"}}/>
  const fileIcon = <ArticleOutlinedIcon sx={{fontSize:"16px", marginTop:"4px", marginRight:"5px"}}/>
  const icon = node.type == "file"? fileIcon:folderIcon
  return (
  <Box sx={style.base}>
    <Box sx={{ ...style.title, display: "flex" }}>
      {icon}
      {`${node.name}`}
    </Box>
  </Box>
  )}
