import math

## https://github.com/taki0112/Vector_Similarity

## max similarity: 1, min: -1
def cosineSimilarity(vec1, vec2) :
    result = innerProduct(vec1,vec2) / (vectorSize(vec1) * vectorSize(vec2))
    return result

def vectorSize(vec) :
    return math.sqrt(sum(math.pow(v,2) for v in vec))

def innerProduct(vec1, vec2) :
    return sum(v1*v2 for v1,v2 in zip(vec1,vec2))

## max similarity: 0, min: inf
def euclideanSimilarity(vec1, vec2) :
    return math.sqrt(sum(math.pow((v1-v2),2) for v1,v2 in zip(vec1, vec2)))

def tsTheta(vec1, vec2) :
    return math.acos(cosineSimilarity(vec1,vec2)) + math.radians(10)

## triangle's area similarity (TS)
def triangleAreaSimilarity(vec1, vec2) :
    theta = math.radians(tsTheta(vec1,vec2))
    return (vectorSize(vec1) * vectorSize(vec2) * math.sin(theta)) / 2

def magnitudeDifference(vec1, vec2) :
    return abs(vectorSize(vec1) - vectorSize(vec2))

## sector's area similarity (SS)
def sectorAreaSimilarity(vec1, vec2) :
    ED = euclideanSimilarity(vec1, vec2)
    MD = magnitudeDifference(vec1, vec2)
    theta = tsTheta(vec1, vec2)
    return math.pi * math.pow((ED+MD),2) * theta/360

## max similarity = 0, min: inf
def TS_SS(vec1, vec2) :
    return triangleAreaSimilarity(vec1, vec2) * sectorAreaSimilarity(vec1, vec2)

if __name__ == '__main__':
    # vec1 = [1,2]
    # vec2 = [2,4]
    # print(vec1, 'vs', vec2)
    # print(euclideanSimilarity(vec1,vec2))
    # print(cosineSimilarity(vec1,vec2))
    # print(TS_SS(vec1,vec2))

    vecs = [[1,2],[2,2],[2,3],[4,4],[4,9]]
    for i in range(len(vecs)-1):
        for j in range(i,len(vecs)):
            if i == j: continue
            print(euclideanSimilarity(vecs[i], vecs[j]))
            print(TS_SS(vecs[i], vecs[j]))
