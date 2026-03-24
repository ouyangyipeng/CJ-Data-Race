// case33: 递归函数中的竞争测试
// 测试递归函数调用中的数据竞争

var globalCounter: Int64 = 0

func recursiveFunc(n: Int64) {
    if (n <= 0) {
        return
    }
    globalCounter = globalCounter + 1  // 写全局变量
    recursiveFunc(n - 1)
}

main() {
    spawn {
        recursiveFunc(5)
    }
    
    spawn {
        recursiveFunc(5)
    }
}