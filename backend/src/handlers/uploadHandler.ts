import {getSignedUrl} from '@aws-sdk/s3-request-presigner';
import {PutObjectCommand} from '@aws-sdk/client-s3';
import s3 from '../clients/s3Client';
import {Request, Response} from 'express';


export async function presignedUpload(req: Request, res: Response){
    try{
        const {userId, filename, contentType= 'application/pdf'}= req.body;

        if(!userId || !filename){
            return res.status(400).json({
                error: "userTd  or filename Error"
            });
        }

        if(!process.env.S3_BUCKET){
            return res.status(400).json({error: "S3_BUCKET not configured"});
        }

        const key=`${userId}/back-statements/${Date.now()}/${filename}`

        const command = new PutObjectCommand({
            Bucket: process.env.S3_BUCKET,
            Key: key,
            ContentType: contentType,
        });

        const url= await getSignedUrl(s3, command, {expiresIn: 3600});

        res.status(200).json({
            url,
            key,
            expiresIn: 3600
        });
    }
    catch(error: any){
        console.log("Error generating preSignedUrl: ", error);
        return res.status(400).json({error: "Failed to geenrated preSignedUrl"});
    }
}
