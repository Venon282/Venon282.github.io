class File{
    static getContent(path){
        return fetch(path)
            .then(response => {
                if (!response.ok) {
                    return [response.status, 503]
                }
                return response.text().then(text => [text, 200])
            })
            .catch(error => {return [error, 503]})
    }
}

export default File
