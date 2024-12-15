export function getContent(path){
    return fetch(path)
        .then(response => {
            if (!response.ok) {
                return [response.status, 503]
            }
            return [response.text(), 200]
        })
        .catch(error => {return [error, 503]})
}
